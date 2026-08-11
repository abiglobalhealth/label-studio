import { Button, Typography } from "@humansignal/ui";
import { Space } from "@humansignal/ui/lib/space/space";
import { cn } from "apps/labelstudio/src/utils/bem";
import { Modal } from "apps/labelstudio/src/components/Modal/ModalPopup";
import { API } from "apps/labelstudio/src/providers/ApiProvider";
import { useAtomValue } from "jotai";
import { atomWithQuery } from "jotai-tanstack-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Input } from "../../../components/Form";
import { useToast } from "@humansignal/ui";

const linkAtom = atomWithQuery(() => ({
  queryKey: ["invite-link"],
  async queryFn() {
    const result = await API.invoke("inviteLink");
    return location.origin + result.invite_url;
  },
}));

const ROLE_OPTIONS = [
  { value: "ANNOTATOR", label: "Annotator" },
  { value: "VIEWER", label: "Viewer" },
  { value: "MANAGER", label: "Manager" },
  { value: "ADMIN", label: "Admin" },
];

export function InviteLink({
  opened,
  onOpened,
  onClosed,
}: {
  opened: boolean;
  onOpened?: () => void;
  onClosed?: () => void;
}) {
  const modalRef = useRef<Modal>();
  const [scopedLink, setScopedLink] = useState<string | null>(null);

  useEffect(() => {
    if (modalRef.current && opened) {
      modalRef.current?.show?.();
    } else if (modalRef.current && modalRef.current.visible) {
      modalRef.current?.hide?.();
    }
  }, [opened]);

  return (
    <Modal
      ref={modalRef}
      title="Invite members"
      opened={opened}
      bareFooter={true}
      body={<InvitationModal scopedLink={scopedLink} setScopedLink={setScopedLink} />}
      footer={<InvitationFooter scopedLink={scopedLink} setScopedLink={setScopedLink} />}
      style={{ width: 680, height: 560 }}
      onHide={onClosed}
      onShow={onOpened}
    />
  );
}

const InvitationModal = ({
  scopedLink,
  setScopedLink,
}: {
  scopedLink: string | null;
  setScopedLink: (value: string | null) => void;
}) => {
  const toast = useToast();
  const { data: link } = useAtomValue(linkAtom);
  const [defaultRole, setDefaultRole] = useState("ANNOTATOR");
  const [allTeams, setAllTeams] = useState<Array<{ id: number; title: string }>>([]);
  const [allWorkspaces, setAllWorkspaces] = useState<Array<{ id: number; title: string }>>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string | undefined>();
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | undefined>();
  const [teamIds, setTeamIds] = useState<number[]>([]);
  const [workspaceIds, setWorkspaceIds] = useState<number[]>([]);
  const [maxUses, setMaxUses] = useState("");
  const [lastPresetSummary, setLastPresetSummary] = useState<string | null>(null);

  const activeLink = scopedLink ?? link;
  const roleOptions = useMemo(() => ROLE_OPTIONS, []);
  const roleLabelByValue = useMemo(
    () => Object.fromEntries(ROLE_OPTIONS.map((item) => [item.value, item.label])),
    [],
  );

  const teamOptions = useMemo(
    () => allTeams.map((team) => ({ value: String(team.id), label: team.title })),
    [allTeams],
  );
  const workspaceOptions = useMemo(
    () => allWorkspaces.map((workspace) => ({ value: String(workspace.id), label: workspace.title })),
    [allWorkspaces],
  );

  useEffect(() => {
    let mounted = true;

    Promise.all([API.invoke("teams"), API.invoke("workspaces")])
      .then(([teamsResponse, workspacesResponse]) => {
        if (!mounted) return;
        const teams = teamsResponse?.results ?? teamsResponse ?? [];
        const workspaces = workspacesResponse?.results ?? workspacesResponse ?? [];

        setAllTeams(teams);
        setAllWorkspaces(workspaces);
      })
      .catch(() => {
        if (!mounted) return;
        setAllTeams([]);
        setAllWorkspaces([]);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const addTeam = useCallback(() => {
    const parsedTeamId = Number(selectedTeamId);
    if (!parsedTeamId || teamIds.includes(parsedTeamId)) return;
    setTeamIds((prev) => [...prev, parsedTeamId]);
    setSelectedTeamId(undefined);
  }, [selectedTeamId, teamIds]);

  const removeTeam = useCallback((teamId: number) => {
    setTeamIds((prev) => prev.filter((id) => id !== teamId));
  }, []);

  const addWorkspace = useCallback(() => {
    const parsedWorkspaceId = Number(selectedWorkspaceId);
    if (!parsedWorkspaceId || workspaceIds.includes(parsedWorkspaceId)) return;
    setWorkspaceIds((prev) => [...prev, parsedWorkspaceId]);
    setSelectedWorkspaceId(undefined);
  }, [selectedWorkspaceId, workspaceIds]);

  const removeWorkspace = useCallback((workspaceId: number) => {
    setWorkspaceIds((prev) => prev.filter((id) => id !== workspaceId));
  }, []);

  const createScopedLink = useCallback(async () => {
    const body: Record<string, unknown> = { default_role: defaultRole };

    const parsedMaxUses = Number(maxUses);

    if (teamIds.length) body.team_ids = teamIds;
    if (workspaceIds.length) body.workspace_ids = workspaceIds;
    if (maxUses && Number.isInteger(parsedMaxUses) && parsedMaxUses > 0) body.max_uses = parsedMaxUses;

    const result = await API.invoke("createInviteLink", {}, { body });

    if (result?.$meta?.ok && result?.invite_url) {
      setScopedLink(location.origin + result.invite_url);
      const selectedTeamTitles = allTeams
        .filter((team) => teamIds.includes(team.id))
        .map((team) => team.title);
      const selectedWorkspaceTitles = allWorkspaces
        .filter((workspace) => workspaceIds.includes(workspace.id))
        .map((workspace) => workspace.title);
      const summary = [
        `Role: ${roleLabelByValue[defaultRole] ?? defaultRole}`,
        `Teams: ${selectedTeamTitles.length ? selectedTeamTitles.join(", ") : "None"}`,
        `Workspaces: ${selectedWorkspaceTitles.length ? selectedWorkspaceTitles.join(", ") : "None"}`,
        `Max Uses: ${maxUses && Number.isInteger(parsedMaxUses) && parsedMaxUses > 0 ? parsedMaxUses : "Unlimited"}`,
      ].join(" · ");

      setLastPresetSummary(summary);
      toast.show({ message: "Scoped invite link created" });
      return;
    }

    toast.show({ message: "Failed to create scoped link", type: "error" });
  }, [defaultRole, teamIds, workspaceIds, maxUses, setScopedLink, toast, allTeams, allWorkspaces, roleLabelByValue]);

  return (
    <div className={cn("invite").toClassName()}>
      <Input value={activeLink} style={{ width: "100%" }} readOnly />
      {lastPresetSummary && (
        <Typography size="small" className="text-neutral-content-subtler mt-tight mb-tight">
          {lastPresetSummary}
        </Typography>
      )}

      <div className="grid gap-2 mt-wide" style={{ maxHeight: 360, overflowY: "auto", paddingBottom: 8 }}>
        <div className="text-neutral-content-subtle text-[13px] font-medium">Create scoped invite link</div>
        <label className="text-neutral-content-subtle text-[12px]">Default role</label>
        <select
          value={defaultRole}
          onChange={(event) => setDefaultRole(event.target.value)}
          className="h-10 rounded border border-neutral-border bg-neutral-background px-3"
        >
          {roleOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <label className="text-neutral-content-subtle text-[12px]">Assign teams</label>
        <div className="flex gap-2">
          <select
            value={selectedTeamId ?? ""}
            onChange={(event) => setSelectedTeamId(event.target.value || undefined)}
            className="h-10 rounded border border-neutral-border bg-neutral-background px-3 flex-1"
          >
            <option value="">Select team</option>
            {teamOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <Button look="outlined" onClick={addTeam} aria-label="Add team to invite preset">
            Add
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {teamIds.map((teamId) => {
            const team = allTeams.find((item) => item.id === teamId);
            if (!team) return null;
            return (
              <Button key={`team-${teamId}`} look="outlined" onClick={() => removeTeam(teamId)}>
                {team.title} ×
              </Button>
            );
          })}
        </div>

        <label className="text-neutral-content-subtle text-[12px]">Assign workspaces</label>
        <div className="flex gap-2">
          <select
            value={selectedWorkspaceId ?? ""}
            onChange={(event) => setSelectedWorkspaceId(event.target.value || undefined)}
            className="h-10 rounded border border-neutral-border bg-neutral-background px-3 flex-1"
          >
            <option value="">Select workspace</option>
            {workspaceOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <Button look="outlined" onClick={addWorkspace} aria-label="Add workspace to invite preset">
            Add
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {workspaceIds.map((workspaceId) => {
            const workspace = allWorkspaces.find((item) => item.id === workspaceId);
            if (!workspace) return null;
            return (
              <Button key={`workspace-${workspaceId}`} look="outlined" onClick={() => removeWorkspace(workspaceId)}>
                {workspace.title} ×
              </Button>
            );
          })}
        </div>

        <Input
          value={maxUses}
          onChange={(eventOrValue) =>
            setMaxUses(typeof eventOrValue === "string" ? eventOrValue : eventOrValue?.target?.value ?? "")
          }
          placeholder="Max uses (optional), e.g. 10"
        />
        <Button onClick={createScopedLink} look="outlined" aria-label="Create scoped invite link">
          Create scoped link
        </Button>
      </div>

      <Typography size="small" className="text-neutral-content-subtler mt-base mb-wider">
        Invite members to join your Label Studio instance. Access to projects and actions depends on their assigned
        role and workspace permissions.{" "}
        <a
          href="https://labelstud.io/guide/signup.html"
          target="_blank"
          rel="noreferrer"
          className="hover:underline"
          onClick={() =>
            __lsa("docs.organization.add_people.learn_more", {
              href: "https://labelstud.io/guide/signup.html",
            })
          }
        >
          Learn more
        </a>
        .
      </Typography>
    </div>
  );
};

const InvitationFooter = ({
  scopedLink,
  setScopedLink,
}: {
  scopedLink: string | null;
  setScopedLink: (value: string | null) => void;
}) => {
  const { copyText, copied } = useTextCopy();
  const { refetch, data: link } = useAtomValue(linkAtom);
  const activeLink = scopedLink ?? link;

  const resetBaseLink = useCallback(async () => {
    await API.invoke("resetInviteLink");
    setScopedLink(null);
    await refetch();
  }, [refetch, setScopedLink]);

  return (
    <Space spread>
      <Space>
        <Button
          variant="negative"
          look="outlined"
          style={{ width: 170 }}
          onClick={resetBaseLink}
          aria-label="Refresh invite link"
        >
          Reset Link
        </Button>
      </Space>
      <Space>
        <Button
          variant={copied ? "positive" : "primary"}
          className="w-[170px]"
          onClick={() => copyText(activeLink ?? "")}
          aria-label="Copy invite link"
        >
          {copied ? "Copied!" : "Copy link"}
        </Button>
      </Space>
    </Space>
  );
};

function useTextCopy() {
  const [copied, setCopied] = useState(false);

  const copyText = useCallback((value: string) => {
    setCopied(true);
    navigator.clipboard.writeText(value ?? "");
    setTimeout(() => setCopied(false), 1500);
  }, []);

  return { copied, copyText };
}
