declare module "inty" {
  interface IntyConfig {
    baseURL?: string;
    apiKey?: string;
  }

  interface IntyApiNode {
    (...args: unknown[]): Promise<unknown>;
    [key: string]: IntyApiNode;
  }

  export class Inty {
    constructor(config?: IntyConfig);
    api: IntyApiNode;
  }
}
