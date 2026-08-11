import { format } from "date-fns";
import { useEffect, useMemo, useState } from "react";
import { NavLink } from "react-router-dom";
import { IconCross } from "@humansignal/icons";
import { Userpic, Button, Select } from "@humansignal/ui";
import { useToast } from "@humansignal/ui";
import { cn } from "../../../utils/bem";
import { useAPI } from "../../../providers/ApiProvider";
import { useAuth } from "@humansignal/core/providers/AuthProvider";
import { hasPermission } from "../../../utils/permissions";
import "./SelectedUser.prefix.css";

const UserProjectsLinks = ({ projects }) => {
  const safeProjects = Array.isArray(projects) ? projects.filter((project) => project && project.id) : [];

  return (
    <div className={cn("user-info").elem("links-list").toClassName()}>
      {safeProjects.map((project) => (
        <NavLink
          className={cn("user-info").elem("project-link").toClassName()}
          key={`project-${project.id}`}
          to={`/projects/${project.id}`}
          data-external
        >
          {project.title}
        </NavLink>
      ))}
    </div>
  );
};

const ROLE_OPTIONS = [
  { value: "OWNER", label: "Owner" },
  { value: "ADMIN", label: "Admin" },
  { value: "MANAGER", label: "Manager" },
  { value: "ANNOTATOR", label: "Annotator" },
  { value: "VIEWER", label: "Viewer" },
];

export const SelectedUser = ({ membership, onClose, onRoleChanged }) => {
  const api = useAPI();
  const toast = useToast();
  const { user: currentUser } = useAuth();
  const selectedUser = membership?.user ?? {};
  const role = membership?.role;
  const createdProjects = Array.isArray(membership?.created_projects)
    ? membership.created_projects
    : Array.isArray(selectedUser?.created_projects)
      ? selectedUser.created_projects
      : [];
  const contributedProjects = Array.isArray(membership?.contributed_to_projects)
    ? membership.contributed_to_projects
    : Array.isArray(selectedUser?.contributed_to_projects)
      ? selectedUser.contributed_to_projects
      : [];
  const [currentRole, setCurrentRole] = useState(role);
  const currentOrgRole = String(currentUser?.active_organization_role ?? "").toUpperCase();
  const isOwner = currentOrgRole === "OWNER";
  const isManager = currentOrgRole === "MANAGER";
  const canManageRoles = isOwner || hasPermission(currentUser, "organizations.members.role");
  const roleOptions = isManager
    ? ROLE_OPTIONS.filter(({ value }) => ["ANNOTATOR", "VIEWER"].includes(value))
    : ROLE_OPTIONS;

  const roleDisabled = useMemo(() => {
    if (!canManageRoles) return true;
    if (role === "OWNER") return true;
    if (isManager && !["ANNOTATOR", "VIEWER"].includes(role)) return true;
    return false;
  }, [canManageRoles, isManager, role]);

  const updateRole = async (newRole) => {
    if (!currentUser?.active_organization) return;
    if (!selectedUser?.id) return;
    const resolvedRole =
      typeof newRole === "string"
        ? newRole
        : typeof newRole?.value === "string"
          ? newRole.value
          : undefined;

    if (!resolvedRole) return;

    const previousRole = currentRole;
    setCurrentRole(resolvedRole);

    try {
      const response = await api.callApi("updateUserMembershipRole", {
        params: { pk: currentUser?.active_organization, userPk: selectedUser.id },
        body: { role: resolvedRole },
      });

      if (response?.role) {
        const normalizedUser =
          response.user && typeof response.user === "object" ? { ...selectedUser, ...response.user } : selectedUser;

        onRoleChanged?.({
          ...membership,
          ...response,
          user: normalizedUser,
          role: response.role ?? resolvedRole,
        });
        toast.show({ message: "Role updated" });
      } else {
        setCurrentRole(previousRole);
        toast.show({ message: "Role update failed", type: "error" });
      }
    } catch {
      setCurrentRole(previousRole);
      toast.show({ message: "Role update failed", type: "error" });
    }
  };

  const fullName = [selectedUser?.first_name, selectedUser?.last_name]
    .filter((n) => !!n)
    .join(" ")
    .trim();

  useEffect(() => {
    setCurrentRole(typeof role === "string" && role ? role : "ANNOTATOR");
  }, [role]);

  const lastActivityDate = selectedUser?.last_activity ? new Date(selectedUser.last_activity) : null;
  const hasValidLastActivity = Boolean(lastActivityDate) && !Number.isNaN(lastActivityDate.getTime());

  return (
    <div className={cn("user-info").toClassName()}>
      <Button
        look="string"
        onClick={onClose}
        className="absolute top-[20px] right-[24px]"
        aria-label="Close user details"
      >
        <IconCross />
      </Button>

      <div className={cn("user-info").elem("header").toClassName()}>
        <Userpic user={selectedUser} style={{ width: 64, height: 64, fontSize: 28 }} />
        <div className={cn("user-info").elem("info-wrapper").toClassName()}>
          {fullName && <div className={cn("user-info").elem("full-name").toClassName()}>{fullName}</div>}
          <p className={cn("user-info").elem("email").toClassName()}>{selectedUser?.email ?? "Unknown user"}</p>
        </div>
      </div>

      {selectedUser?.phone && (
        <div className={cn("user-info").elem("section").toClassName()}>
          <a href={`tel:${selectedUser.phone}`}>{selectedUser.phone}</a>
        </div>
      )}

      <div className={cn("user-info").elem("section").toClassName()}>
        <div className={cn("user-info").elem("section-title").toClassName()}>Role</div>
        <Select
          value={currentRole}
          options={roleOptions}
          disabled={roleDisabled}
          onChange={updateRole}
          aria-label="Change organization role"
        />
      </div>

      {!!createdProjects.length && (
        <div className={cn("user-info").elem("section").toClassName()}>
          <div className={cn("user-info").elem("section-title").toClassName()}>Created Projects</div>

          <UserProjectsLinks projects={createdProjects} />
        </div>
      )}

      {!!contributedProjects.length && (
        <div className={cn("user-info").elem("section").toClassName()}>
          <div className={cn("user-info").elem("section-title").toClassName()}>Contributed to</div>

          <UserProjectsLinks projects={contributedProjects} />
        </div>
      )}

      <p className={cn("user-info").elem("last-active").toClassName()}>
        Last activity on: {hasValidLastActivity ? format(lastActivityDate, "dd MMM yyyy, KK:mm a") : "Unknown"}
      </p>
    </div>
  );
};
