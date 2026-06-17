/** Legacy readable_id when present; otherwise User.id (companion guest rows). */
export function userDisplayId(user: {
  id: string;
  readable_id?: string | null;
}): string {
  const readableId = user.readable_id?.trim();
  if (readableId) {
    return readableId;
  }
  return user.id;
}
