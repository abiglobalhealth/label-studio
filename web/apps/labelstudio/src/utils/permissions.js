export const hasPermission = (user, permission) => {
  const permissions = user?.permissions ?? [];
  return permissions.includes(permission);
};

export const hasAnyPermission = (user, requiredPermissions = []) => {
  return requiredPermissions.some((permission) => hasPermission(user, permission));
};
