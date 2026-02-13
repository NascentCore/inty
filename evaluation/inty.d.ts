declare module "inty" {
  interface IntyConfig {
    baseURL?: string;
    apiKey?: string;
  }

  export class Inty {
    constructor(config?: IntyConfig);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    api: any;
  }
}
