declare module "inty" {
  interface IntyConfig {
    baseURL?: string;
    apiKey?: string;
  }

  export class Inty {
    constructor(config?: IntyConfig);
    api: unknown;
  }
}
