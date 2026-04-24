import { TeamViewPage } from "@/src/features/team-view/TeamViewPage";

export default async function DraftViewRoute({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  return <TeamViewPage teamId={teamId} />;
}
