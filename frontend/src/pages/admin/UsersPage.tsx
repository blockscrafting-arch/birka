import { useEffect, useMemo, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useAdminUsers, useUpdateUserRole } from "../../hooks/useAdmin";

const roles = ["client", "warehouse", "admin"] as const;

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

export function UsersPage() {
  const [searchInput, setSearchInput] = useState("");
  const search = useDebouncedValue(searchInput, 300);
  const { items: users = [], isLoading, error } = useAdminUsers(search || undefined);
  const updateRole = useUpdateUserRole();
  const [draftRoles, setDraftRoles] = useState<Record<number, string>>({});

  const sortedUsers = useMemo(() => {
    return [...users].sort((a, b) => b.created_at.localeCompare(a.created_at));
  }, [users]);

  const handleRoleChange = (userId: number, role: string) => {
    setDraftRoles((prev) => ({ ...prev, [userId]: role }));
  };

  const handleSave = (userId: number, currentRole: string) => {
    const role = draftRoles[userId] ?? currentRole;
    updateRole.mutate({ id: userId, role });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-lg font-semibold text-slate-900">Пользователи</div>
        <Input
          type="search"
          placeholder="Поиск по имени, @username, Telegram ID..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {isLoading ? <div className="text-sm text-slate-600">Загрузка пользователей...</div> : null}
      {error ? <div className="text-sm text-rose-500">Ошибка загрузки пользователей</div> : null}

      <div className="space-y-3">
        {sortedUsers.map((user) => {
          const displayName = [user.first_name, user.last_name].filter(Boolean).join(" ") || "Без имени";
          const roleValue = draftRoles[user.id] ?? user.role;
          return (
            <div key={user.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
              <div className="text-sm font-semibold text-slate-900">{displayName}</div>
              <div className="text-xs text-slate-500">Telegram ID: {user.telegram_id}</div>
              {user.telegram_username ? (
                <div className="text-xs text-slate-500">@{user.telegram_username}</div>
              ) : null}
              <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
                <Select value={roleValue} onChange={(e) => handleRoleChange(user.id, e.target.value)}>
                  {roles.map((role) => (
                    <option key={role} value={role}>
                      {role}
                    </option>
                  ))}
                </Select>
                <Button
                  variant="secondary"
                  onClick={() => handleSave(user.id, user.role)}
                  disabled={updateRole.isPending}
                >
                  Сохранить
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
