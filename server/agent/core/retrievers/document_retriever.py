import logging

from django.db.models import QuerySet
from enthusiast_common.config import AgentConfig
from enthusiast_common.registry import BaseEmbeddingProviderRegistry
from enthusiast_common.retrievers import BaseVectorStoreRetriever
from enthusiast_common.structures import RepositoriesInstances
from langchain_core.language_models import BaseLanguageModel
from pgvector.django import CosineDistance

from catalog.models import DocumentChunk

logger = logging.getLogger(__name__)


class DocumentRetriever(BaseVectorStoreRetriever[DocumentChunk]):
    def find_content_matching_query(self, query: str) -> QuerySet[DocumentChunk]:
        logger.info(f"[DocumentRetriever] Querying docs for: '{query}' (data_set_id={self.data_set_id})")
        try:
            embedding_vector = self._create_embedding_for_query(query)
            logger.info(f"[DocumentRetriever] Embedding generated, dim={len(embedding_vector)}")
        except Exception as exc:
            logger.error(f"[DocumentRetriever] Embedding generation FAILED ({type(exc).__name__}): {exc}")
            raise
        relevant_documents = self._find_documents_matching_vector(embedding_vector)
        count = relevant_documents.count()
        logger.info(f"[DocumentRetriever] Vector search returned {count} chunks (max_objects={self.max_objects})")
        if count == 0:
            logger.warning(
                f"[DocumentRetriever] ⚠ No document chunks found — "
                f"documents may not be indexed for data_set_id={self.data_set_id}."
            )
        return relevant_documents

    def _create_embedding_for_query(self, query: str) -> list[float]:
        data_set = self.data_set_repo.get_by_id(self.data_set_id)
        logger.info(
            f"[DocumentRetriever] Embedding model='{data_set.embedding_model}' "
            f"dim={data_set.embedding_vector_dimensions}"
        )
        embedding_provider = self.embeddings_registry.provider_for_dataset(self.data_set_id)
        return embedding_provider(data_set.embedding_model, data_set.embedding_vector_dimensions).generate_embeddings(
            query
        )

    def _find_documents_matching_vector(self, embedding_vector: list[float]) -> QuerySet[DocumentChunk]:
        embedding_distance = CosineDistance("embedding", embedding_vector)
        embeddings_with_documents = self.model_chunk_repo.get_chunk_by_distance_for_data_set(
            self.data_set_id, embedding_distance
        )
        limited_embeddings_with_documents = embeddings_with_documents[: self.max_objects]
        return limited_embeddings_with_documents

    @classmethod
    def create(
        cls,
        config: AgentConfig,
        data_set_id: int,
        repositories: RepositoriesInstances,
        embeddings_registry: BaseEmbeddingProviderRegistry,
        llm: BaseLanguageModel,
    ) -> BaseVectorStoreRetriever[DocumentChunk]:
        return cls(
            data_set_id=data_set_id,
            data_set_repo=repositories.data_set,
            model_chunk_repo=repositories.document_chunk,
            embeddings_registry=embeddings_registry,
            **config.retrievers.document.extra_kwargs,
        )
