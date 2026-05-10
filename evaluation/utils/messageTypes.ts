const USER_MESSAGE_TYPES = new Set(["human", "HumanMessage", "user", "USER"]);

export const isUserMessageType = (
  messageType: string | null | undefined,
): boolean => {
  if (!messageType) {
    return false;
  }
  return USER_MESSAGE_TYPES.has(messageType);
};
