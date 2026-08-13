import { Button } from "@humansignal/ui";
import { useCallback, useMemo, useRef, useState } from "react";
import { useUpdatePageTitle } from "@humansignal/core";
import { HeidiTips } from "../../../components/HeidiTips/HeidiTips";
import { modal } from "../../../components/Modal/Modal";
import { Space } from "../../../components/Space/Space";
import { cn } from "../../../utils/bem";
import { FF_AUTH_TOKENS, FF_LSDV_E_297, isFF } from "../../../utils/feature-flags";
import "./PeopleInvitation.prefix.css";
import { PeopleList } from "./PeopleList";
import "./PeoplePage.prefix.css";
import { TokenSettingsModal } from "@humansignal/app-common/blocks/TokenSettingsModal";
import { IconPlus } from "@humansignal/icons";
import { useToast } from "@humansignal/ui";
import { InviteLink } from "./InviteLink";
import { SelectedUser } from "./SelectedUser";
import { useAuth } from "@humansignal/core/providers/AuthProvider";
import { hasPermission } from "../../../utils/permissions";

export const PeoplePage = () => {
  const apiSettingsModal = useRef();
  const { user } = useAuth();
  const toast = useToast();
  const [selectedMembership, setSelectedMembership] = useState(null);
  const [membersReloadToken, setMembersReloadToken] = useState(0);
  const [invitationOpen, setInvitationOpen] = useState(false);
  const canInvite = hasPermission(user, "organizations.members.invite");

  useUpdatePageTitle("People");

  const selectUser = useCallback(
    (membership) => {
      setSelectedMembership(membership);

      if (membership?.user?.id) {
        localStorage.setItem("selectedUser", membership.user.id);
      } else {
        localStorage.removeItem("selectedUser");
      }
    },
    [setSelectedMembership],
  );

  const apiTokensSettingsModalProps = useMemo(
    () => ({
      title: "API Token Settings",
      style: { width: 480 },
      body: () => (
        <TokenSettingsModal
          onSaved={() => {
            toast.show({ message: "API Token settings saved" });
            apiSettingsModal.current?.close();
          }}
        />
      ),
    }),
    [],
  );

  const showApiTokenSettingsModal = useCallback(() => {
    apiSettingsModal.current = modal(apiTokensSettingsModalProps);
    __lsa("organization.token_settings");
  }, [apiTokensSettingsModalProps]);

  const defaultSelected = useMemo(() => {
    return localStorage.getItem("selectedUser");
  }, []);

  return (
    <div className={cn("people").toClassName()}>
      <div className={cn("people").elem("controls").toClassName()}>
        <Space spread>
          <Space />

          <Space>
            {isFF(FF_AUTH_TOKENS) && (
              <Button look="outlined" onClick={showApiTokenSettingsModal} aria-label="Show API token settings">
                API Tokens Settings
              </Button>
            )}
            <Button
              leading={<IconPlus className="!h-4" />}
              onClick={() => setInvitationOpen(true)}
              aria-label="Invite new member"
              disabled={!canInvite}
            >
              Add Members
            </Button>
          </Space>
        </Space>
      </div>
      <div className={cn("people").elem("content").toClassName()}>
        <PeopleList
          selectedUser={selectedMembership?.user}
          defaultSelected={defaultSelected}
          onSelect={selectUser}
          reloadToken={membersReloadToken}
        />

        {selectedMembership ? (
          <SelectedUser
            membership={selectedMembership}
            onClose={() => selectUser(null)}
            onRoleChanged={(membership) => {
              selectUser(membership);
              setMembersReloadToken((token) => token + 1);
            }}
          />
        ) : (
          isFF(FF_LSDV_E_297) && <HeidiTips collection="organizationPage" />
        )}
      </div>
      <InviteLink
        opened={invitationOpen}
        onClosed={() => {
          console.log("hidden");
          setInvitationOpen(false);
        }}
      />
    </div>
  );
};

PeoplePage.title = "People";
PeoplePage.path = "/";
