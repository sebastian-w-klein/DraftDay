"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { NFL_TEAMS } from "@/lib/teams";

export function AppNav() {
  const [team, setTeam] = useState("TEN");
  const normalizedTeam = useMemo(() => team.trim().toUpperCase() || "TEN", [team]);

  return (
    <header className="mb-6 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">DraftDay</h1>
          <p className="text-sm text-slate-300">Consensus, intelligence, and team/coach context in one place.</p>
        </div>
        <nav className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
          <Link href="/" className="rounded bg-indigo-700 px-3 py-2 text-center text-sm font-medium hover:bg-indigo-600">
            Overall Draft Predictions
          </Link>
          <div className="flex items-center gap-2">
            <select
              value={team}
              onChange={(e) => setTeam(e.target.value.toUpperCase())}
              className="w-24 rounded border border-slate-700 bg-slate-950 px-2 py-2 text-sm"
              aria-label="Team abbreviation"
            >
              {NFL_TEAMS.map((abbr) => (
                <option key={abbr} value={abbr}>
                  {abbr}
                </option>
              ))}
            </select>
            <Link
              href={`/teams/${normalizedTeam}/draft-view`}
              className="rounded border border-slate-600 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-slate-800"
            >
              Team/Coach View
            </Link>
          </div>
        </nav>
      </div>
    </header>
  );
}
