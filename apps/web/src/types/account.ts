export type Account = {
  id: string;
  label: string;
  email_hint: string | null;
  is_active: boolean;
  has_gpmc_auth_data: boolean;
  has_gptk_cookie_jar: boolean;
  created_at: string;
  updated_at: string;
};
