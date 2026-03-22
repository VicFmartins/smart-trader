export type AuthenticatedUser = {
  id: number;
  email: string;
  fullName: string | null;
  isActive: boolean;
  isAdmin: boolean;
  createdAt: string;
};

export type AuthSession = {
  accessToken: string;
  tokenType: string;
  expiresAt: string;
  user: AuthenticatedUser;
};
