declare module "inty" {
  export interface IntyConfig {
    baseURL: string;
    apiKey: string;
  }

  export interface IntyClient {
    api: {
      v1: {
        uploadImage: (payload: {
          file: File;
          cropping_avatar?: boolean;
        }) => Promise<{
          data?: {
            avatar_url?: string;
            url?: string;
          };
        }>;
        ai: {
          agents: {
            create: (payload: unknown) => Promise<{ data?: unknown }>;
            update: (
              agentId: string,
              payload: unknown,
            ) => Promise<{ data?: unknown }>;
            retrieve: (agentId: string) => Promise<unknown>;
            delete: (agentId: string) => Promise<unknown>;
          };
        };
      };
    };
  }

  export class Inty implements IntyClient {
    constructor(config: IntyConfig);
    api: IntyClient["api"];
  }
}
