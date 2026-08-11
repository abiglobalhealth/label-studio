import { useCallback, useEffect, useMemo, useState } from "react";
import { Redirect } from "react-router-dom";
import { Button, Select } from "@humansignal/ui";
import { useAPI } from "../../providers/ApiProvider";
import { useAuth } from "@humansignal/core/providers/AuthProvider";
import { hasPermission } from "../../utils/permissions";
import { cn } from "../../utils/bem";
import { Input } from "../../components/Form";
import "./WorkspacesPage.prefix.css";

export const WorkspacesPage = () => {
  const api = useAPI();
  const { user } = useAuth();
  const role = String(user?.active_organization_role ?? "").toUpperCase();
  const canAccessPage = role === "OWNER" || role === "ADMIN";
  const canManage = hasPermission(user, "workspaces.change");
  const canCreate = hasPermission(user, "workspaces.create");
  const canDelete = hasPermission(user, "workspaces.delete");

  const [workspaces, setWorkspaces] = useState([]);
  const [teams, setTeams] = useState([]);
  const [members, setMembers] = useState([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState();
  const [newWorkspaceTitle, setNewWorkspaceTitle] = useState("");
  const [selectedUserId, setSelectedUserId] = useState();
  const [selectedTeamId, setSelectedTeamId] = useState();
  const [userAssignments, setUserAssignments] = useState([]);
  const [teamAssignments, setTeamAssignments] = useState([]);

  const selectedWorkspace = useMemo(
    () => workspaces.find((workspace) => workspace.id === selectedWorkspaceId),
    [workspaces, selectedWorkspaceId],
  );

  const fetchWorkspaces = useCallback(async () => {
    const response = await api.callApi("workspaces");
    const list = response.results ?? response ?? [];
    setWorkspaces(list);
    if (list.length && !selectedWorkspaceId) setSelectedWorkspaceId(list[0].id);
  }, [api, selectedWorkspaceId]);

  const fetchAssignments = useCallback(async () => {
    if (!selectedWorkspaceId) return;
    const [usersResponse, teamsResponse] = await Promise.all([
      api.callApi("workspaceUserAssignments"),
      api.callApi("workspaceTeamAssignments"),
    ]);
    const users = usersResponse.results ?? usersResponse ?? [];
    const assignedTeams = teamsResponse.results ?? teamsResponse ?? [];
    setUserAssignments(users.filter((item) => item.workspace === selectedWorkspaceId));
    setTeamAssignments(assignedTeams.filter((item) => item.workspace === selectedWorkspaceId));
  }, [api, selectedWorkspaceId]);

  const fetchTeams = useCallback(async () => {
    const response = await api.callApi("teams");
    setTeams(response.results ?? response ?? []);
  }, [api]);

  const fetchMembers = useCallback(async () => {
    if (!user?.active_organization) return;
    const response = await api.callApi("memberships", {
      params: { pk: user.active_organization, page_size: 1000 },
    });
    setMembers((response.results ?? response ?? []).map((membership) => membership.user));
  }, [api, user?.active_organization]);

  useEffect(() => {
    if (!canAccessPage) return;
    fetchWorkspaces();
    fetchTeams();
    fetchMembers();
  }, [canAccessPage, fetchWorkspaces, fetchTeams, fetchMembers]);

  useEffect(() => {
    if (canAccessPage) fetchAssignments();
  }, [canAccessPage, fetchAssignments]);

  if (!canAccessPage) return <Redirect to="/organization" />;

  const getInputValue = (value) => (typeof value === "string" ? value : value?.target?.value ?? "");
  const userOptions = members.map((member) => ({ value: String(member.id), label: member.email }));
  const teamOptions = teams.map((team) => ({ value: String(team.id), label: team.title }));
  const assignedUsers = userAssignments
    .map((assignment) => members.find((member) => member.id === assignment.user))
    .filter(Boolean);
  const assignedTeams = teamAssignments
    .map((assignment) => teams.find((team) => team.id === assignment.team))
    .filter(Boolean);

  const createWorkspace = async () => {
    if (!newWorkspaceTitle.trim()) return;
    await api.callApi("createWorkspace", { body: { title: newWorkspaceTitle.trim() } });
    setNewWorkspaceTitle("");
    await fetchWorkspaces();
  };

  const deleteWorkspace = async () => {
    if (!selectedWorkspaceId) return;
    await api.callApi("deleteWorkspace", { params: { pk: selectedWorkspaceId } });
    setSelectedWorkspaceId(undefined);
    await fetchWorkspaces();
  };

  const addAssignment = async (endpoint, body, reset) => {
    if (!selectedWorkspaceId) return;
    await api.callApi(endpoint, { body: { workspace: selectedWorkspaceId, ...body } });
    reset();
    await fetchAssignments();
  };

  const removeAssignment = async (endpoint, id) => {
    await api.callApi(endpoint, { params: { pk: id } });
    await fetchAssignments();
  };

  return (
    <div className={cn("workspaces-page").toClassName()}>
      <div className={cn("workspaces-page").elem("header").toClassName()}>
        <h2>Workspaces</h2>
        <div className={cn("workspaces-page").elem("create").toClassName()}>
          <Input
            value={newWorkspaceTitle}
            placeholder="New workspace name"
            onChange={(value) => setNewWorkspaceTitle(getInputValue(value))}
          />
          <Button onClick={createWorkspace} disabled={!canCreate} aria-label="Create workspace">
            Create
          </Button>
        </div>
      </div>

      <div className={cn("workspaces-page").elem("content").toClassName()}>
        <div className={cn("workspaces-page").elem("list").toClassName()}>
          {workspaces.map((workspace) => (
            <button
              key={workspace.id}
              className={cn("workspaces-page")
                .elem("workspace-item")
                .mod({ active: workspace.id === selectedWorkspaceId })
                .toClassName()}
              onClick={() => setSelectedWorkspaceId(workspace.id)}
            >
              {workspace.title}
            </button>
          ))}
        </div>

        {selectedWorkspace && (
          <div className={cn("workspaces-page").elem("details").toClassName()}>
            <div className={cn("workspaces-page").elem("details-head").toClassName()}>
              <h3>{selectedWorkspace.title}</h3>
              <Button look="outlined" variant="negative" onClick={deleteWorkspace} disabled={!canDelete}>
                Delete
              </Button>
            </div>
            <div className={cn("workspaces-page").elem("section").toClassName()}>
              <h4>Workspace ID</h4>
              <p>{selectedWorkspace.id}</p>
            </div>

            <div className={cn("workspaces-page").elem("section").toClassName()}>
              <h4>Users with access</h4>
              <div className={cn("workspaces-page").elem("assign").toClassName()}>
                <Select value={selectedUserId} onChange={setSelectedUserId} options={userOptions} placeholder="Select user" />
                <Button
                  onClick={() => addAssignment("createWorkspaceUserAssignment", { user: Number(selectedUserId) }, () => setSelectedUserId(undefined))}
                  disabled={!canManage || !selectedUserId}
                >
                  Assign user
                </Button>
              </div>
              <ul>
                {assignedUsers.map((member) => {
                  const assignment = userAssignments.find((item) => item.user === member.id);
                  return (
                    <li key={member.id}>
                      <span>{member.email}</span>
                      <Button look="string" onClick={() => removeAssignment("deleteWorkspaceUserAssignment", assignment.id)} disabled={!canManage}>
                        Remove
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className={cn("workspaces-page").elem("section").toClassName()}>
              <h4>Teams with access</h4>
              <div className={cn("workspaces-page").elem("assign").toClassName()}>
                <Select value={selectedTeamId} onChange={setSelectedTeamId} options={teamOptions} placeholder="Select team" />
                <Button
                  onClick={() => addAssignment("createWorkspaceTeamAssignment", { team: Number(selectedTeamId) }, () => setSelectedTeamId(undefined))}
                  disabled={!canManage || !selectedTeamId}
                >
                  Assign team
                </Button>
              </div>
              <ul>
                {assignedTeams.map((team) => {
                  const assignment = teamAssignments.find((item) => item.team === team.id);
                  return (
                    <li key={team.id}>
                      <span>{team.title}</span>
                      <Button look="string" onClick={() => removeAssignment("deleteWorkspaceTeamAssignment", assignment.id)} disabled={!canManage}>
                        Remove
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

WorkspacesPage.title = "Workspaces";
WorkspacesPage.path = "/workspaces";
