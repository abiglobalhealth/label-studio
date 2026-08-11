import React, { useState } from "react";
import { useParams as useRouterParams } from "react-router";
import { Redirect } from "react-router-dom";
import { Button, Checkbox, Select } from "@humansignal/ui";
import { Oneof } from "../../components/Oneof/Oneof";
import { Spinner } from "../../components/Spinner/Spinner";
import { ApiContext } from "../../providers/ApiProvider";
import { useContextProps } from "../../providers/RoutesProvider";
import { cn } from "../../utils/bem";
import { CreateProject } from "../CreateProject/CreateProject";
import { DataManagerPage } from "../DataManager/DataManager";
import { SettingsPage } from "../Settings";
import { EmptyProjectsList, ProjectsList } from "./ProjectsList";
import { useAbortController, useUpdatePageTitle } from "@humansignal/core";
import { useAuth } from "@humansignal/core/providers/AuthProvider";
import { hasPermission } from "../../utils/permissions";
import "./Projects.prefix.css";

const getCurrentPage = () => {
  const pageNumberFromURL = new URLSearchParams(location.search).get("page");

  return pageNumberFromURL ? Number.parseInt(pageNumberFromURL) : 1;
};

export const ProjectsPage = () => {
  const api = React.useContext(ApiContext);
  const { user } = useAuth();
  const abortController = useAbortController();
  const [projectsList, setProjectsList] = React.useState([]);
  const [networkState, setNetworkState] = React.useState(null);
  const [currentPage, setCurrentPage] = useState(getCurrentPage());
  const [totalItems, setTotalItems] = useState(1);
  const [includeArchived, setIncludeArchived] = useState(false);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState();
  const [selectedTopicId, setSelectedTopicId] = useState();
  const [workspaces, setWorkspaces] = useState([]);
  const [topics, setTopics] = useState([]);
  const setContextProps = useContextProps();

  const canCreateProjects = hasPermission(user, "projects.create");
  const canManageProjects = hasPermission(user, "projects.change");

  useUpdatePageTitle("Projects");
  const defaultPageSize = Number.parseInt(localStorage.getItem("pages:projects-list") ?? 30);

  const [modal, setModal] = React.useState(false);

  const openModal = () => setModal(true);

  const closeModal = () => setModal(false);

  const fetchProjects = async (page = currentPage, pageSize = defaultPageSize) => {
    setNetworkState("loading");
    abortController.renew();

    const requestParams = {
      page,
      page_size: pageSize,
      include_archived: includeArchived,
    };

    if (selectedWorkspaceId) requestParams.workspace_id = selectedWorkspaceId;
    if (selectedTopicId) requestParams.topic = String(selectedTopicId);

    requestParams.include = [
      "id",
      "title",
      "created_by",
      "created_at",
      "color",
      "is_published",
      "assignment_settings",
      "state",
      "workspace",
      "topic",
      "topic_title",
      "archived_at",
    ].join(",");

    const data = await api.callApi("projects", {
      params: requestParams,
      signal: abortController.controller.current.signal,
      errorFilter: (e) => e.error.includes("aborted"),
    });

    setTotalItems(data?.count ?? 1);
    setProjectsList(data.results ?? []);
    setNetworkState("loaded");

    if (data?.results?.length) {
      const additionalData = await api.callApi("projects", {
        params: {
          ids: data?.results?.map(({ id }) => id).join(","),
          include: [
            "id",
            "description",
            "num_tasks_with_annotations",
            "task_number",
            "skipped_annotations_number",
            "total_annotations_number",
            "total_predictions_number",
            "ground_truth_number",
            "finished_task_number",
            "workspace",
            "topic",
            "topic_title",
            "archived_at",
          ].join(","),
          include_archived: includeArchived,
          page_size: pageSize,
        },
        signal: abortController.controller.current.signal,
        errorFilter: (e) => e.error.includes("aborted"),
      });

      if (additionalData?.results?.length) {
        setProjectsList((prev) =>
          additionalData.results.map((project) => {
            const prevProject = prev.find(({ id }) => id === project.id);

            return {
              ...prevProject,
              ...project,
            };
          }),
        );
      }
    }
  };

  const loadNextPage = async (page, pageSize) => {
    setCurrentPage(page);
    await fetchProjects(page, pageSize);
  };

  const fetchWorkspaceAndTopicOptions = async () => {
    const [workspaceResponse, topicResponse] = await Promise.all([api.callApi("workspaces"), api.callApi("topics")]);
    setWorkspaces(Array.isArray(workspaceResponse) ? workspaceResponse : workspaceResponse?.results ?? []);
    setTopics(Array.isArray(topicResponse) ? topicResponse : topicResponse?.results ?? []);
  };

  const archiveProject = async (projectId) => {
    await api.callApi("archiveProject", { params: { pk: projectId } });
    await fetchProjects(currentPage, defaultPageSize);
  };

  const restoreProject = async (projectId) => {
    await api.callApi("restoreProject", { params: { pk: projectId } });
    await fetchProjects(currentPage, defaultPageSize);
  };

  React.useEffect(() => {
    fetchProjects();
    fetchWorkspaceAndTopicOptions();
  }, []);

  React.useEffect(() => {
    fetchProjects(1, defaultPageSize);
  }, [includeArchived, selectedWorkspaceId, selectedTopicId]);

  React.useEffect(() => {
    setContextProps({ openModal, showButton: projectsList.length > 0 && canCreateProjects });
  }, [projectsList.length, canCreateProjects]);

  const workspaceOptions = workspaces.map((workspace) => ({
    value: workspace.id,
    label: workspace.title,
  }));

  const topicOptions = topics.map((topic) => ({
    value: String(topic.id),
    label: topic.title,
  }));

  const resetFilters = () => {
    setIncludeArchived(false);
    setSelectedWorkspaceId(undefined);
    setSelectedTopicId(undefined);
    setCurrentPage(1);
  };

  return (
    <div className={cn("projects-page").toClassName()}>
      <Oneof value={networkState}>
        <div className={cn("projects-page").elem("loading").toClassName()} case="loading">
          <Spinner size={64} />
        </div>
        <div className={cn("projects-page").elem("content").toClassName()} case="loaded">
          <div className={cn("projects-page").elem("filters").toClassName()}>
            <Checkbox
              checked={includeArchived}
              onChange={(eventOrValue) => {
                const checked =
                  typeof eventOrValue === "boolean" ? eventOrValue : Boolean(eventOrValue?.target?.checked);

                setIncludeArchived(checked);
              }}
            >
              Include archived
            </Checkbox>
            <Select
              value={selectedWorkspaceId}
              onChange={(value) => setSelectedWorkspaceId(value || undefined)}
              options={[{ value: "", label: "All workspaces" }, ...workspaceOptions]}
              placeholder="Filter by workspace"
            />
            <Select
              value={selectedTopicId ? String(selectedTopicId) : undefined}
              onChange={(value) => setSelectedTopicId(value || undefined)}
              options={[{ value: "", label: "All topics" }, ...topicOptions]}
              placeholder="Filter by topic"
            />
            <Button look="outlined" onClick={resetFilters} aria-label="Clear project filters">
              Clear filters
            </Button>
          </div>

          {projectsList.length ? (
            <ProjectsList
              projects={projectsList}
              currentPage={currentPage}
              totalItems={totalItems}
              loadNextPage={loadNextPage}
              pageSize={defaultPageSize}
              canManageProjects={canManageProjects}
              onArchiveProject={archiveProject}
              onRestoreProject={restoreProject}
              topics={topics}
            />
          ) : (
            <EmptyProjectsList openModal={openModal} canCreateProjects={canCreateProjects} />
          )}
          {modal && canCreateProjects && <CreateProject onClose={closeModal} />}
        </div>
      </Oneof>
    </div>
  );
};

ProjectsPage.title = "Projects";
ProjectsPage.path = "/projects";
ProjectsPage.exact = true;
ProjectsPage.routes = ({ store }) => [
  {
    title: () => store.project?.title,
    path: "/:id(\\d+)",
    exact: true,
    component: () => {
      const params = useRouterParams();

      return <Redirect to={`/projects/${params.id}/data`} />;
    },
    pages: {
      DataManagerPage,
      SettingsPage,
    },
  },
];
ProjectsPage.context = ({ openModal, showButton }) => {
  if (!showButton) return null;
  return (
    <Button onClick={openModal} size="small" aria-label="Create new project">
      Create
    </Button>
  );
};
