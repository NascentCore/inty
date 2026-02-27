const GITHUB_ISSUE_URL_REGEX =
  /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/issues\/\d+\/?(?:[?#].*)?$/;

export const normalizeGithubIssueUrlInput = (input: string): string | null => {
  const normalized = input.trim();
  return normalized ? normalized : null;
};

export const isValidGithubIssueUrl = (url: string): boolean =>
  GITHUB_ISSUE_URL_REGEX.test(url);
