import { formatDistance } from "date-fns";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge, Userpic } from "@humansignal/ui";
import { Pagination, Spinner } from "../../../components";
import { usePage, usePageSize } from "../../../components/Pagination/Pagination";
import { useAPI } from "../../../providers/ApiProvider";
import { useAuth } from "@humansignal/core/providers/AuthProvider";
import { cn } from "../../../utils/bem";
import { isDefined } from "../../../utils/helpers";
import "./PeopleList.prefix.css";
import { CopyableTooltip } from "../../../components/CopyableTooltip/CopyableTooltip";

export const PeopleList = ({ onSelect, selectedUser, defaultSelected, reloadToken }) => {
  const api = useAPI();
  const { user: currentUser } = useAuth();
  const [usersList, setUsersList] = useState();
  const [currentPage] = usePage("page", 1);
  const [currentPageSize] = usePageSize("page_size", 30);
  const [totalItems, setTotalItems] = useState(0);
  const autoSelectedUserIdRef = useRef(null);

  const formatLastActivity = (dateValue) => {
    if (!dateValue) return "Unknown";

    const parsedDate = new Date(dateValue);
    if (Number.isNaN(parsedDate.getTime())) return "Unknown";

    return formatDistance(parsedDate, new Date(), { addSuffix: true });
  };

  const fetchUsers = useCallback(async (page, pageSize) => {
    if (!currentUser?.active_organization) return;

    const response = await api.callApi("memberships", {
      params: {
        pk: currentUser?.active_organization,
        contributed_to_projects: 1,
        page,
        page_size: pageSize,
      },
    });

    if (response.results) {
      const normalized = (response.results ?? []).filter((membership) => membership?.user && membership?.user?.id);
      setUsersList(normalized);
      setTotalItems(response.count);
    }
  }, [api, currentUser?.active_organization]);

  const selectUser = useCallback(
    (membership) => {
      const user = membership?.user;
      if (!user?.id) return;

      if (selectedUser?.id === user?.id) {
        onSelect?.(null);
      } else {
        onSelect?.(membership);
      }
    },
    [onSelect, selectedUser],
  );

  const selectUserWithoutToggle = useCallback(
    (membership) => {
      const user = membership?.user;
      if (!user?.id) return;
      onSelect?.(membership);
    },
    [onSelect],
  );

  useEffect(() => {
    if (!currentUser?.active_organization) return;
    fetchUsers(currentPage, currentPageSize);
  }, [fetchUsers, currentUser?.active_organization, currentPage, currentPageSize, reloadToken]);

  useEffect(() => {
    if (isDefined(defaultSelected) && usersList) {
      const selected = usersList.find((membership) => membership?.user?.id === Number(defaultSelected));

      if (selected && autoSelectedUserIdRef.current !== selected.user.id) {
        autoSelectedUserIdRef.current = selected.user.id;
        selectUserWithoutToggle(selected);
      }
    }
  }, [usersList, defaultSelected, selectUserWithoutToggle]);

  return (
    <>
      <div className={cn("people-list").toClassName()}>
        <div className={cn("people-list").elem("wrapper").toClassName()}>
          {usersList ? (
            <div className={cn("people-list").elem("users").toClassName()}>
                <div className={cn("people-list").elem("header").toClassName()}>
                  <div className={cn("people-list").elem("column").mix("avatar").toClassName()} />
                  <div className={cn("people-list").elem("column").mix("email").toClassName()}>Email</div>
                  <div className={cn("people-list").elem("column").mix("name").toClassName()}>Name</div>
                  <div className={cn("people-list").elem("column").mix("role").toClassName()}>Role</div>
                  <div className={cn("people-list").elem("column").mix("last-activity").toClassName()}>Last Activity</div>
                </div>
              <div className={cn("people-list").elem("body").toClassName()}>
                {usersList.map((membership) => {
                  const { user, role } = membership;
                  const active = user?.id === selectedUser?.id;

                  return (
                    <div
                      key={`user-${user?.id ?? membership?.id}`}
                      className={cn("people-list").elem("user").mod({ active }).toClassName()}
                      onClick={() => selectUser(membership)}
                    >
                      <div className={cn("people-list").elem("field").mix("avatar").toClassName()}>
                        <CopyableTooltip title={`User ID: ${user?.id ?? "n/a"}`} textForCopy={user?.id ?? ""}>
                          <Userpic user={user} style={{ width: 28, height: 28 }} />
                        </CopyableTooltip>
                      </div>
                      <div className={cn("people-list").elem("field").mix("email").toClassName()}>{user?.email ?? "Unknown"}</div>
                      <div className={cn("people-list").elem("field").mix("name").toClassName()}>
                        {user?.first_name ?? ""} {user?.last_name ?? ""}
                      </div>
                      <div className={cn("people-list").elem("field").mix("role").toClassName()}>
                        <Badge size="small" variant="neutral" shape="rounded">
                          {role ?? "-"}
                        </Badge>
                      </div>
                      <div className={cn("people-list").elem("field").mix("last-activity").toClassName()}>
                        {formatLastActivity(user?.last_activity)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className={cn("people-list").elem("loading").toClassName()}>
              <Spinner size={36} />
            </div>
          )}
        </div>
        <Pagination
          page={currentPage}
          urlParamName="page"
          totalItems={totalItems}
          pageSize={currentPageSize}
          pageSizeOptions={[30, 50, 100]}
          onPageLoad={fetchUsers}
          style={{ paddingTop: 16 }}
        />
      </div>
    </>
  );
};
