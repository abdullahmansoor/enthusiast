import logging
import re
from difflib import SequenceMatcher
from typing import Self

from django.db import DatabaseError
from django.db.models import Q

logger = logging.getLogger(__name__)
from enthusiast_common.builder import RepositoriesInstances
from enthusiast_common.config import AgentConfig
from enthusiast_common.registry import BaseEmbeddingProviderRegistry
from enthusiast_common.repositories import BaseDataSetRepository, BaseProductRepository
from enthusiast_common.retrievers import BaseProductRetriever
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import PromptTemplate

from catalog.models import Product

QUERY_PROMPT_TEMPLATE = """
    With the following database schema delimited by three backticks ```
    CREATE TABLE catalog_product (
        \"id\" int8 NOT NULL,
        \"entry_id\" varchar NOT NULL,
        \"name\" varchar NOT NULL,
        \"slug\" varchar NOT NULL,
        \"description\" text NOT NULL,
        \"sku\" varchar NOT NULL,
        \"properties\" varchar NOT NULL,
        \"categories\" varchar NOT NULL,
        \"price\" float8 NOT NULL,
        PRIMARY KEY (\"id\")
    );```
    that contains product information, with some example values delimited by three backticks
    ```
    {sample_products_json}
    ```
    generate a where clause for an SQL query for fetching products that can be useful when answering the following
    request delimited by three backticks.
    Make sure that the queries are case insensitive
    ```
    {query}
    ```
    Respond with the where portion of the query only, don't include any other characters,
    skip initial where keyword, skip order by clause.
"""


class ProductRetriever(BaseProductRetriever):
    def __init__(
        self,
        data_set_id: int,
        data_set_repo: BaseDataSetRepository,
        product_repo: BaseProductRepository,
        llm: BaseLanguageModel,
        prompt_template: str,
        number_of_products: int = 300,
        max_sample_products: int = 300,
    ):
        self.data_set_id = data_set_id
        self.data_set_repo = data_set_repo
        self.product_repo = product_repo
        self.number_of_products = number_of_products
        self.max_sample_products = max_sample_products
        self.prompt_template = prompt_template
        self.llm = llm

    def find_products_matching_query(self, user_query: str) -> list[Product]:
        fallback_conditions = [f"data_set_id = {self.data_set_id}"]

        try:
            agent_where_clause = self._build_where_clause_for_query(user_query)
        except Exception as exc:
            logger.warning(f"[ProductRetriever] LLM WHERE-clause generation failed ({type(exc).__name__}: {exc}), using dataset fallback.")
            agent_where_clause = ""

        if agent_where_clause:
            where_conditions = fallback_conditions + [agent_where_clause]
            logger.info(f"[ProductRetriever] Executing WHERE: {where_conditions}")
            try:
                results = list(self.product_repo.extra(where_conditions=where_conditions)[: self.number_of_products])
                logger.info(f"[ProductRetriever] LLM WHERE returned {len(results)} products.")
            except DatabaseError as exc:
                logger.warning(
                    f"[ProductRetriever] WHERE clause caused DB error ({type(exc).__name__}): {exc} | "
                    f"clause='{agent_where_clause[:200]}' — falling back to full dataset."
                )
                results = []
            if results:
                return results
            logger.info(
                f"[ProductRetriever] LLM WHERE returned 0 products, trying fuzzy match. "
                f"clause='{agent_where_clause[:200]}'"
            )

        fuzzy_results = self._find_products_by_fuzzy_match(user_query)
        if fuzzy_results:
            logger.info(f"[ProductRetriever] Fuzzy match returned {len(fuzzy_results)} products.")
            return fuzzy_results

        logger.info(f"[ProductRetriever] Using dataset fallback: data_set_id={self.data_set_id}")
        fallback_results = list(self.product_repo.extra(where_conditions=fallback_conditions)[: self.number_of_products])
        logger.info(f"[ProductRetriever] Fallback returned {len(fallback_results)} products.")
        return fallback_results

    def get_sample_products_json(self) -> str:
        import json
        sample_products = list(self.product_repo.filter(data_set_id__exact=self.data_set_id)[: self.max_sample_products])
        serialized = json.dumps([
            {"name": p.name, "price": p.price, "description": p.description[:200] if p.description else "", "categories": p.categories, "sku": p.sku}
            for p in sample_products
        ])
        logger.debug(f"[ProductRetriever] Sample products JSON ({len(sample_products)} items, {len(serialized)} chars)")
        return serialized

    def _build_where_clause_for_query(self, query: str) -> str:
        chain = PromptTemplate.from_template(self.prompt_template) | self.llm
        llm_result = chain.invoke({"sample_products_json": self.get_sample_products_json(), "query": query})
        raw_content = llm_result.content
        logger.info(f"[ProductRetriever] LLM raw output for query='{query}': '''{raw_content}'''")

        # Strip markdown fences, sql prefix, leading/trailing whitespace
        sanitized = raw_content.strip("`").removeprefix("sql").strip()
        # Remove leading WHERE keyword if the LLM included it despite instructions
        sanitized = re.sub(r"(?i)^\s*where\s+", "", sanitized).strip()
        # Escape bare % so Django's extra() doesn't treat them as printf placeholders
        sanitized = sanitized.replace("%", "%%")

        logger.info(f"[ProductRetriever] Sanitized WHERE clause for query='{query}': '{sanitized}'")
        return sanitized

    def _find_products_by_fuzzy_match(self, query: str) -> list[Product]:
        tokens = self._tokenize_query(query)
        base_qs = self.product_repo.filter(data_set_id__exact=self.data_set_id)
        if tokens:
            text_query = Q()
            for token in tokens:
                text_query |= Q(name__icontains=token)
                text_query |= Q(categories__icontains=token)
                text_query |= Q(description__icontains=token)
                text_query |= Q(sku__icontains=token)
            results = list(base_qs.filter(text_query)[: self.number_of_products])
            if results:
                return results

        # Typo-tolerant fallback: rank by similarity on name/categories
        candidates = list(base_qs[: max(self.number_of_products, 200)])
        scored = []
        query_norm = query.strip().lower()
        for product in candidates:
            name = (product.name or "").lower()
            categories = (product.categories or "").lower()
            score = max(
                SequenceMatcher(None, query_norm, name).ratio(),
                SequenceMatcher(None, query_norm, categories).ratio(),
            )
            if score >= 0.5:
                scored.append((score, product))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [product for _, product in scored[: self.number_of_products]]

    @staticmethod
    def _tokenize_query(query: str) -> list[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s]+", " ", query).lower()
        raw_tokens = [token for token in cleaned.split() if len(token) >= 3]
        stopwords = {
            "what",
            "are",
            "is",
            "do",
            "does",
            "you",
            "have",
            "any",
            "the",
            "a",
            "an",
            "of",
            "for",
            "to",
            "with",
            "related",
            "products",
            "product",
            "category",
            "categories",
        }
        tokens = [token for token in raw_tokens if token not in stopwords]
        expanded = set(tokens)
        for token in tokens:
            if token.endswith("s") and len(token) > 4:
                expanded.add(token[:-1])
            else:
                expanded.add(f"{token}s")
        return list(expanded)

    @classmethod
    def create(
        cls,
        config: AgentConfig,
        data_set_id: int,
        repositories: RepositoriesInstances,
        embeddings_registry: BaseEmbeddingProviderRegistry,
        llm: BaseLanguageModel,
    ) -> Self:
        return cls(
            data_set_id=data_set_id,
            data_set_repo=repositories.data_set,
            product_repo=repositories.product,
            llm=llm,
            **config.retrievers.product.extra_kwargs,
        )
