import { useCallback, useEffect, useMemo, useState } from "react";
import { Redirect } from "react-router-dom";
import { Button, Select } from "@humansignal/ui";
import { useAPI } from "../../providers/ApiProvider";
import { useAuth } from "@humansignal/core/providers/AuthProvider";
import { hasPermission } from "../../utils/permissions";
import { cn } from "../../utils/bem";
import { Input } from "../../components/Form";
import "./TeamsPage.prefix.css";

export const TeamsPage = () => {
  const api = useAPI();
  const { user } = useAuth();
  const role = String(user?.active_organization_role ?? "").toUpperCase();
  const canAccessPage = role === "OWNER" || role === "ADMIN";
  // Keep the role check as a fallback while a freshly changed role is still
  // propagating through the auth provider's permissions list.
  const canManage = ["OWNER", "ADMIN"].includes(role) || hasPermission(user, "teams.change");
  const [teams, setTeams] = useState([]);
  const [members, setMembers] = useState([]);
  const [managers, setManagers] = useState([]);
  const [teamMembers, setTeamMembers] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState();
  const [newTeamTitle, setNewTeamTitle] = useState("");
  const [newTeamDescription, setNewTeamDescription] = useState("");
  const [teamDescription, setTeamDescription] = useState("");
  const [selectedManagerId, setSelectedManagerId] = useState();
  const [selectedMemberId, setSelectedMemberId] = useState();

  const selectedTeam = useMemo(() => teams.find((team) => team.id === selectedTeamId), [teams, selectedTeamId]);
  const getInputValue = (value) => (typeof value === "string" ? value : value?.target?.value ?? "");

  useEffect(() => {
    setTeamDescription(selectedTeam?.description ?? "");
  }, [selectedTeamId, selectedTeam?.description]);

  const fetchTeams = useCallback(async () => {
    const response = await api.callApi("teams");
    const list = Array.isArray(response) ? response : response?.results ?? [];
    setTeams(list);
    if (list.length && !selectedTeamId) setSelectedTeamId(list[0].id);
  }, [api, selectedTeamId]);

  const fetchMembers = useCallback(async () => {
    if (!user?.active_organization) return;
    const response = await api.callApi("memberships", {
      params: { pk: user.active_organization, page_size: 1000 },
    });
    const memberships = Array.isArray(response) ? response : response?.results ?? [];
    setMembers(
      memberships
        .map((membership) => {
          const member = membership?.user ?? membership;
          return member?.id ? { ...member, role: membership?.role ?? member.role } : null;
        })
        .filter(Boolean),
    );
  }, [api, user?.active_organization]);

  const fetchAssignments = useCallback(async () => {
    if (!selectedTeamId) return;
    const [managerResponse, memberResponse] = await Promise.all([
      api.callApi("teamManagers"),
      api.callApi("teamMembers"),
    ]);
    const managerList = Array.isArray(managerResponse) ? managerResponse : managerResponse?.results ?? [];
    const memberList = Array.isArray(memberResponse) ? memberResponse : memberResponse?.results ?? [];
    setManagers(managerList.filter((item) => item.team === selectedTeamId));
    setTeamMembers(memberList.filter((item) => item.team === selectedTeamId));
  }, [api, selectedTeamId]);

  useEffect(() => {
    if (!canAccessPage) return;
    fetchTeams();
    fetchMembers();
  }, [canAccessPage, fetchTeams, fetchMembers]);

  useEffect(() => {
    if (canAccessPage) fetchAssignments();
  }, [canAccessPage, fetchAssignments]);

  if (!canAccessPage) return <Redirect to="/organization" />;

  const managerOptions = members
    .filter((member) => ["OWNER", "ADMIN", "MANAGER"].includes(String(member.role ?? "").toUpperCase()))
    .map((member) => ({ value: String(member.id), label: member.email }));
  const memberOptions = members.map((member) => ({ value: String(member.id), label: member.email }));
  const userById = new Map(members.map((member) => [member.id, member]));

  const createTeam = async () => {
    if (!newTeamTitle.trim()) return;
    const response = await api.callApi("createTeam", {
      body: { title: newTeamTitle.trim(), description: newTeamDescription.trim() },
    });
    setNewTeamTitle("");
    setNewTeamDescription("");
    if (response?.id) {
      setTeams((currentTeams) => [...currentTeams, response]);
      setSelectedTeamId(response.id);
    } else {
      await fetchTeams();
    }
  };

  const deleteTeam = async () => {
    if (!selectedTeamId) return;
    await api.callApi("deleteTeam", { params: { pk: selectedTeamId } });
    setSelectedTeamId(undefined);
    await fetchTeams();
  };

  const updateTeamDescription = async () => {
    if (!selectedTeamId) return;
    const response = await api.callApi("updateTeam", {
      params: { pk: selectedTeamId },
      body: { description: teamDescription },
    });
    if (response?.id) {
      setTeams((currentTeams) => currentTeams.map((team) => (team.id === response.id ? response : team)));
    }
  };

  const addManager = async () => {
    if (!selectedTeamId || !selectedManagerId) return;
    await api.callApi("createTeamManager", { body: { team: selectedTeamId, user: Number(selectedManagerId) } });
    setSelectedManagerId(undefined);
    await fetchAssignments();
  };

  const addMember = async () => {
    if (!selectedTeamId || !selectedMemberId) return;
    await api.callApi("createTeamMember", { body: { team: selectedTeamId, user: Number(selectedMemberId) } });
    setSelectedMemberId(undefined);
    await fetchAssignments();
  };

  return (
    <div className={cn("teams-page").toClassName()}>
      <div className={cn("teams-page").elem("header").toClassName()}>
        <h2>Teams</h2>
        <div className={cn("teams-page").elem("create").toClassName()}>
          <Input value={newTeamTitle} placeholder="Team name" onChange={(value) => setNewTeamTitle(getInputValue(value))} />
          <Input
            value={newTeamDescription}
            placeholder="Description"
            onChange={(value) => setNewTeamDescription(getInputValue(value))}
          />
          <Button onClick={createTeam} disabled={!canManage}>
            Create team
          </Button>
        </div>
      </div>
      <div className={cn("teams-page").elem("content").toClassName()}>
        <div className={cn("teams-page").elem("list").toClassName()}>
          {teams.map((team) => (
            <button
              key={team.id}
              className={cn("teams-page").elem("team-item").mod({ active: team.id === selectedTeamId }).toClassName()}
              onClick={() => setSelectedTeamId(team.id)}
            >
              <strong>{team.title}</strong>
              {team.description && <small>{team.description}</small>}
            </button>
          ))}
        </div>
        {selectedTeam && (
          <div className={cn("teams-page").elem("details").toClassName()}>
            <div className={cn("teams-page").elem("details-head").toClassName()}>
              <h3>{selectedTeam.title}</h3>
              <Button look="outlined" variant="negative" onClick={deleteTeam} disabled={!canManage}>
                Delete
              </Button>
            </div>
            <div className={cn("teams-page").elem("description").toClassName()}>
              <Input
                value={teamDescription}
                placeholder="Description"
                onChange={(value) => setTeamDescription(getInputValue(value))}
                disabled={!canManage}
              />
              <Button
                onClick={updateTeamDescription}
                disabled={!canManage || teamDescription === (selectedTeam.description ?? "")}
              >
                Save description
              </Button>
            </div>
            <section>
              <h4>Managers</h4>
              <div className={cn("teams-page").elem("assign").toClassName()}>
                <Select value={selectedManagerId} onChange={setSelectedManagerId} options={managerOptions} placeholder="Select Manager" />
                <Button onClick={addManager} disabled={!canManage || !selectedManagerId}>Assign Manager</Button>
              </div>
              <ul>
                {managers.map((assignment) => (
                  <li key={assignment.id}>
                    {userById.get(assignment.user)?.email ?? assignment.user}
                    <Button look="string" onClick={() => api.callApi("deleteTeamManager", { params: { pk: assignment.id } }).then(fetchAssignments)} disabled={!canManage}>
                      Remove
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h4>Members</h4>
              <div className={cn("teams-page").elem("assign").toClassName()}>
                <Select value={selectedMemberId} onChange={setSelectedMemberId} options={memberOptions} placeholder="Select member" />
                <Button onClick={addMember} disabled={!canManage || !selectedMemberId}>Add member</Button>
              </div>
              <ul>
                {teamMembers.map((assignment) => (
                  <li key={assignment.id}>
                    {userById.get(assignment.user)?.email ?? assignment.user}
                    <Button look="string" onClick={() => api.callApi("deleteTeamMember", { params: { pk: assignment.id } }).then(fetchAssignments)} disabled={!canManage}>
                      Remove
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
          </div>
        )}
      </div>
    </div>
  );
};

TeamsPage.title = "Teams";
TeamsPage.path = "/teams";
