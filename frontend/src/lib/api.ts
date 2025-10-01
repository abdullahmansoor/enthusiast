import { AuthenticationProvider } from "./authentication-provider.ts";
import { UsersApiClient } from "@/lib/api/users.ts";
import { CatalogApiClient } from "@/lib/api/catalog.ts";
import { DataSetsApiClient } from "@/lib/api/data-sets.ts";
import { ConversationsApiClient } from "@/lib/api/conversations.ts";
import { ServiceAccountsApiClient } from "@/lib/api/service-accounts.ts";
import { Account, SourcePlugin, User } from "@/lib/types.ts";
import { ConfigApiClient } from "@/lib/api/config.ts";
import {AgentsApiClient} from "@/lib/api/agents.ts";

export type Token = {
  token: string;
}

type AccountResponse = {
  email: string;
  is_staff: boolean;
}

export type FeedbackData = {
  rating: number | null;
  feedback: string;
}

export type TaskHandle = {
  task_id: string;
  streaming: boolean;
}

export class ApiClient {
  private readonly apiBase: string;
  private csrfPrimed = false;


  constructor(private readonly authenticationProvider: AuthenticationProvider) {
    this.apiBase = import.meta.env.VITE_API_BASE;
  }

  private async ensureCsrf(): Promise<void> {
    if (this.csrfPrimed) return;
    // This endpoint must exist on the API and set the csrftoken cookie
    // e.g. Django view with @ensure_csrf_cookie returning 204
    await fetch(`${this.apiBase}/api/auth/csrf/`, { credentials: 'include' });
    this.csrfPrimed = true;
  }

  private getCookie(name: string): string | undefined {
    return document.cookie
      .split('; ')
      .find(c => c.startsWith(name + '='))?.split('=')[1];
  }

  async login(email: string, password: string): Promise<Token> {
    await this.ensureCsrf();
    const csrftoken = this.getCookie('csrftoken') ?? '';

    const response = await fetch(`${this.apiBase}/api/auth/login`, {
      method: 'POST',
      credentials: 'include',                 // <-- send/receive cookies
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,             // <-- echo CSRF cookie
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      // Try to surface a helpful error
      let detail = '';
      try { detail = JSON.stringify(await response.json()); } catch {}
      throw new Error(`Login failed: ${response.status} ${response.statusText} ${detail}`);
    }

    // If your API returns a token in JSON, keep this:
    try {
      const data = await response.json();
      return data as Token;
    } catch {
      // If it’s session-only (no JSON body), return a dummy/tokenless object or adjust the return type
      return { token: '' };
    }
  }
  async login_old(email: string, password: string): Promise<Token> {
    const response = await fetch(`${this.apiBase}/api/auth/login`, {
      headers: {
        'Content-Type': 'application/json'
      },
      method: 'POST',
      body: JSON.stringify({ email, password })
    });

    if (response.status !== 200) {
      throw 'Could not sign in';
    }

    return await response.json() as Promise<Token>;
  }

  async getAccount(): Promise<Account> {
    const response = await fetch(`${this.apiBase}/api/account`, this._requestConfiguration());
    const responseJson = await response.json() as AccountResponse;
    return {
      email: responseJson.email,
      isStaff: responseJson.is_staff
    };
  }

  users(): UsersApiClient {
    return new UsersApiClient(this.apiBase, this.authenticationProvider);
  }

  async getAllUsers(): Promise<User[]> {
    const response = await fetch(`${this.apiBase}/api/users?page_size=1000`, this._requestConfiguration());
    return (await response.json()).results as User[];
  }

  async getAllProductSourcePlugins(): Promise<SourcePlugin[]> {
    const response = await fetch(`${this.apiBase}/api/plugins/product_source_plugins?page_size=1000`, this._requestConfiguration());
    return (await response.json()).choices as SourcePlugin[];
  }

  async getAllDocumentSourcePlugins(): Promise<SourcePlugin[]> {
    const response = await fetch(`${this.apiBase}/api/plugins/document_source_plugins?page_size=1000`, this._requestConfiguration());
    return (await response.json()).choices as SourcePlugin[];
  }  

  catalog(): CatalogApiClient {
    return new CatalogApiClient(this.apiBase, this.authenticationProvider);
  }

  serviceAccounts(): ServiceAccountsApiClient {
    return new ServiceAccountsApiClient(this.apiBase, this.authenticationProvider);
  }

  dataSets(): DataSetsApiClient {
    return new DataSetsApiClient(this.apiBase, this.authenticationProvider);
  }

  conversations(): ConversationsApiClient {
    return new ConversationsApiClient(this.apiBase, this.authenticationProvider);
  }

  config(): ConfigApiClient {
    return new ConfigApiClient(this.apiBase, this.authenticationProvider);
  }

  agents(): AgentsApiClient {
    return new AgentsApiClient(this.apiBase, this.authenticationProvider);
  }

  _requestConfiguration(): RequestInit {
    return {
      headers: {
        'Authorization': `Token ${this.authenticationProvider.token}`,
        "Content-Type": "application/json"
      }
    }
  }
}
