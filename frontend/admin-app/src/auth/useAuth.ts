import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  queryKeys,
  type CurrentUser,
  type LoginRequest,
} from "@palms/shared";

import { useApiClient } from "@/api/ApiClientProvider";
import { hasPermission, type PermissionCode } from "@/auth/permissions";
import { useSnackbarStore } from "@/stores/uiStore";
import { getErrorMessage } from "@/utils/errors";

export function useCurrentUser(
  enabled = true,
): UseQueryResult<CurrentUser, Error> {
  const client = useApiClient();
  return useQuery({
    queryKey: queryKeys.me,
    queryFn: ({ signal }) => client.auth.me({ signal }),
    enabled,
    retry: false,
    staleTime: 60_000,
  });
}

export function useAuth() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const meQuery = useCurrentUser();

  const loginMutation = useMutation({
    mutationFn: (input: LoginRequest) => client.auth.login(input),
    onSuccess: (data) => {
      if (!data?.user) {
        return;
      }
      queryClient.setQueryData(queryKeys.me, {
        ...data.user,
        two_factor: { enabled: false, mode: "placeholder" as const },
      });
      show("Signed in successfully.", "success");
    },
    onError: (error) => show(getErrorMessage(error, "Login failed."), "error"),
  });

  const logoutMutation = useMutation({
    mutationFn: () => client.auth.logout(),
    onSettled: async () => {
      queryClient.clear();
    },
  });

  const user = meQuery.data;
  const permissions = user?.permissions ?? [];

  return {
    user,
    permissions,
    isLoading: meQuery.isLoading,
    isAuthenticated: Boolean(user),
    isError: meQuery.isError,
    can: (permission: PermissionCode | PermissionCode[]) =>
      hasPermission(permissions, permission),
    login: loginMutation,
    logout: logoutMutation,
    refresh: () => meQuery.refetch(),
  };
}
