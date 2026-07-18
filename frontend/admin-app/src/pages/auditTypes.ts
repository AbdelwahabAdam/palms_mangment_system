export interface Activity {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  message: string | null;
  actor_user_id: string | null;
  created_at: string;
}
