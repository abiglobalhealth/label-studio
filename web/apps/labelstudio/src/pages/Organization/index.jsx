import { SidebarMenu } from "../../components/SidebarMenu/SidebarMenu";
import { useAuth } from "@humansignal/core/providers/AuthProvider";
import { Redirect } from "react-router-dom";
import { PeoplePage } from "./PeoplePage/PeoplePage";
import { WorkspacesPage } from "./WorkspacesPage";
import { TeamsPage } from "./TeamsPage";
import { WebhookPage } from "../WebhookPage/WebhookPage";

const ALLOW_ORGANIZATION_WEBHOOKS = window.APP_SETTINGS.flags?.allow_organization_webhooks;

const MenuLayout = ({ children, ...routeProps }) => {
  const { user } = useAuth();
  const currentOrgRole = String(user?.active_organization_role ?? "").toUpperCase();
  const canManageWorkspaces = ["OWNER", "ADMIN"].includes(currentOrgRole);

  const menuItems = [PeoplePage];

  if (canManageWorkspaces) {
    menuItems.push(TeamsPage);
    menuItems.push(WorkspacesPage);
  }

  if (ALLOW_ORGANIZATION_WEBHOOKS) {
    menuItems.push(WebhookPage);
  }
  return <SidebarMenu menuItems={menuItems} path={routeProps.match.url} children={children} />;
};

const OrganizationAccessGate = () => {
  const { user } = useAuth();
  const currentOrgRole = String(user?.active_organization_role ?? "").toUpperCase();

  if (!["OWNER", "ADMIN", "MANAGER"].includes(currentOrgRole)) {
    return <Redirect to="/projects" />;
  }

  return <PeoplePage />;
};

const organizationPages = { TeamsPage, WorkspacesPage };

if (ALLOW_ORGANIZATION_WEBHOOKS) {
  organizationPages.WebhookPage = WebhookPage;
}

export const OrganizationPage = {
  title: "Organization",
  path: "/organization",
  exact: true,
  layout: MenuLayout,
  component: OrganizationAccessGate,
  pages: organizationPages,
};
