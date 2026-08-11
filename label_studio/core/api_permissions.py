from rest_framework.permissions import SAFE_METHODS, BasePermission


class HasObjectPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.has_permission(request.user)


class RoleBasedPermission(BasePermission):
    """
    Enforce the RBAC permission declared on a view for the current HTTP method.

    Views declare their action-level permission via ``permission_required``:
      * a ``ViewClassPermission`` mapping HTTP method -> permission name, or
      * a plain permission string applied to every method.

    Views without ``permission_required`` are allowed here; they remain
    protected by object-level checks (``HasObjectPermission``) and their own
    queryset scoping. Requests are denied only when the user's role does not
    grant the declared permission (see ``core.rbac.ROLE_PERMISSION_MATRIX``).
    """

    def has_permission(self, request, view):
        required = getattr(view, 'permission_required', None)
        if required is None:
            return True

        if isinstance(required, str):
            permission = required
        else:
            permission = getattr(required, request.method, None)

        if permission is None:
            return True

        # Deferred import: core.rbac pulls in organizations.models -> core.utils.common ->
        # rest_framework.views, which would otherwise cycle while DRF loads the permission
        # classes referenced by DEFAULT_PERMISSION_CLASSES during settings initialization.
        from core.rbac import has_permission as has_rbac_permission

        return has_rbac_permission(request.user, permission)


class MemberHasOwnerPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method not in SAFE_METHODS:
            from core.rbac import can_manage_member

            if not can_manage_member(request.user, obj):
                return False

        return obj.has_permission(request.user)
