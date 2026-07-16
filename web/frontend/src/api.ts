
const BASE_URL = "http://localhost:8000";
interface GroupCreate {
  name: string;
  entry_fee: number;   // coins, matches the backend
  closes_at: string;   // ISO datetime string, e.g. "2026-08-01T18:00:00Z"
  is_public: boolean;  // public = anyone can find it; private = friends only
}

export type CoinPack = "small" | "medium" | "large";

export type RoomPage = {          // paginated envelope from the browse endpoints
  rooms: Room[];
  total: number;
  page: number;
  page_size: number;
};

export type Room = {              // list item (from GET /api/groups, /api/rooms/*)
  id: number;
  name: string;
  entry_fee: number;
  closes_at: string;
  is_public: boolean;
  owner_id: number;
  owner_name: string;             // email prefix, links to /users/:owner_id
  member_count: number;           // active (paid) members
};

export type RoomMember = { id: number; name: string };

export type RoomDetail = Room & { // from GET /api/groups/{id}
  is_open: boolean;
  pot: number;
  member_count: number;
  members: RoomMember[];
  is_member: boolean;
  is_owner: boolean;
};



// one of the benefits of typscript is that we can define the shape of responses
export type PredictResult = {
  fighter_a: string;
  fighter_b: string;
  style_a: string;
  style_b: string;
  prob_a: number;
  prob_b: number;
  pick: string;
  confidence: number;
  // Tale of the tape
  factors: {
    label: string;
    value_a: string;
    value_b: string;
    favors: string;
  }[];
  free_remaining: number | null;   // free predictions left; null = unlimited (subscriber)
};
export type PhaseBout = {
  fight_number: number;
  opponent: string;
  won: boolean;
  event: string;
  adj_perf: number;
};
export type Phase = {
  fights: number;
  win_rate: number;
  raw_perf: number;
  adj_perf: number;
  opp_strength: number;
  bouts: PhaseBout[];
};
export type UserEvents = {
  event_id: number;
  title: string;
  date: number;
  poster: string | null;

}

export type CareerSummary = {
  fighter: string;
  total_fights: number;
  win_rate: number;       // percent
  avg_raw_perf: number;
  avg_adj_perf: number;
  perf_label: string;
  avg_opp_strength: number;
  opp_label: string;
  volatility: number;
  volatility_label: string;
  career_score: number;   // 0–100
  career_label: string;
  trajectory: string | null;
  phases: {
    early: Phase | null;              // can be null
    mid:   Phase | null;
    late:  Phase | null;
  };
  
};

export type Bout = {
  /** {
                        "matchup": f.matchup,
                        "fighter_a": f.fighter_a,
                        "fighter_b": f.fighter_b,
                        "odds_a": f.odds_a,
                        "odds_b": f.odds_b,
                    } */
  id: number;
  matchup: string;
  fighter_a: string;
  fighter_b: string;
  odds_a: string | null;   // can be null
  odds_b: string | null;
  img_a: string | null;
  img_b: string | null;
}
export type UFCEvent = {
  /**
                "title": e.title,
                "event_link": e.event_link,
                "date": e.date,
                "venue": e.venue,
                "poster": e.poster,
                "fights": [ */
  title: string;
  event_link: string;
  date: number;
  venue: string | null;
  poster: string | null;
  fights: Bout[];
  
}
export type NewsArticle = {
  title: string;
  url: string;
  source: string | null;
  published_at: string | null;
  image: string | null;
};
export type TopCareer = {           // shape → export type
  fighter: string;
  career_score: number;
  total_fights: number;
};

export type LoginResponse = { message: string };
export type SignupResponse = { id: number; email: string };
export type MeResponse = { id: number; email: string };

export async function getPublicRooms(q = "", page = 1): Promise<RoomPage> {
  const res = await fetch(
    `${BASE_URL}/api/rooms/public?q=${encodeURIComponent(q)}&page=${page}`,
    { credentials: "include" },
  );
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) throw new Error("Could not load public rooms");
  return res.json() as Promise<RoomPage>;
}

export async function getPrivateRooms(q = "", page = 1): Promise<RoomPage> {
  const res = await fetch(
    `${BASE_URL}/api/rooms/private?q=${encodeURIComponent(q)}&page=${page}`,
    { credentials: "include" },
  );
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) throw new Error("Could not load private rooms");
  return res.json() as Promise<RoomPage>;
}

export async function getBalance(): Promise<number> {
  const res = await fetch(`${BASE_URL}/api/coins/balance`, {
    credentials: "include", // authed endpoint — send the cookie
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) throw new Error("Could not load balance");
  const data: { balance: number } = await res.json();
  return data.balance;
}

export async function buyCoins(pack: CoinPack): Promise<string> {
  
  const res = await fetch(`${BASE_URL}/api/coin/checkout?pack_id=${pack}`, {
    method: "POST",
    credentials: "include",
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not buy coins");
  }
  const data: { url: string } = await res.json();
  return data.url;
}

export async function startSubscription(): Promise<string> {
  // opens a $10/mo subscription checkout; returns the Stripe URL to redirect to
  const res = await fetch(`${BASE_URL}/api/billing/checkout`, {
    method: "POST",
    credentials: "include",
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not start subscription");
  }
  const data: { url: string } = await res.json();
  return data.url;
}

export async function getMyRooms(): Promise<Room[]> {
  const res = await fetch(`${BASE_URL}/api/groups`, {
    credentials: "include",
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) throw new Error("Could not load rooms");
  const data: { groups: Room[] } = await res.json();
  return data.groups;
}

export async function createRoom(body: GroupCreate): Promise<Room> {
  const res = await fetch(`${BASE_URL}/api/groups`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not create room");
  }
  return res.json() as Promise<Room>;
}

export async function getRoom(id: number): Promise<RoomDetail> {
  const res = await fetch(`${BASE_URL}/api/groups/${id}`, {
    credentials: "include",
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) throw new Error("Could not load room");
  return res.json() as Promise<RoomDetail>; // endpoint returns the object directly
}

export async function joinRoom(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/groups/${id}/join`, {
    method: "POST",
    credentials: "include",
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) {
    // backend explains WHY (not enough coins / closed / already in) — surface it
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not join room");
  }
}

export async function getRoomLeaderboard(id: number): Promise<LeaderboardRow[]> {
  const res = await fetch(`${BASE_URL}/api/groups/${id}/leaderboard`, {
    credentials: "include",
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) throw new Error("Could not load room leaderboard");
  const data: { leaderboard: LeaderboardRow[] } = await res.json();
  return data.leaderboard;
}
export async function getUpcomingEvents(): Promise<UFCEvent[]> {
  const res = await fetch(`${BASE_URL}/api/events/upcoming`);
  if (!res.ok) throw new Error("Could not load events");
  const data: { events: UFCEvent[] } = await res.json();
  return data.events;
}

export async function getCareerSummary(fighter: string): Promise<CareerSummary> {
  const res = await  fetch(`${BASE_URL}/api/fighters/${encodeURIComponent(fighter)}/career`);
  if (!res.ok) throw new Error("Could not load career summary");
  const data: CareerSummary = await res.json();
  return data;
}

// Latest news for a query like a fighter. The backend call newsapiu
export async function getNews(q: string): Promise<NewsArticle[]> {
  const res = await fetch(`${BASE_URL}/api/news?q=${encodeURIComponent(q)}`); // make it url safe
  if (!res.ok) throw new Error("Could not load news");
  const data: { query: string; articles: NewsArticle[] } = await res.json();
  return data.articles;
}

// Fetch the list of fighter names for the dropdowns.
export async function getFighters(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/api/fighters`);
  if (!res.ok) throw new Error("Could not load fighters");
  const data: { fighters: string[] } = await res.json();
  return data.fighters;
}
export async function get_user_past_events(userId: number): Promise<UserEvents[]> {
  const res = await fetch(`${BASE_URL}/api/users/${userId}/events`, {
    credentials: "include", // endpoint requires the auth cookie
  });
  if (!res.ok) throw new Error("Could not load events");
  const data: { events: UserEvents[] } = await res.json();
  return data.events;
}

// One fight in a user's event breakdown: who they picked, who won, did they nail it.
export type UserEventFight = {
  event_id: number;
  matchup: string;
  fighter_a: string;
  fighter_b: string;
  img_a: string | null;
  img_b: string | null;
  picked: string;
  winner: string | null;   // null until the fight is settled
  correct: boolean;
};

// A user's stats for one event: summary numbers + the per-fight breakdown.
export type UserEventStats = {
  user_id: number;
  event_id: number | null;
  picks_made: number;
  fights_settled: number;
  correct: number;
  winrate: number | null;  // null until at least one fight settles
  fights: UserEventFight[];
};

export async function getUserEventStats(
  userId: number,
  eventId: number,
): Promise<UserEventStats> {
  const res = await fetch(
    `${BASE_URL}/api/users/${userId}/stats?event_id=${eventId}`,
    { credentials: "include" }, // endpoint requires the auth cookie
  );
  if (!res.ok) throw new Error("Could not load event stats");
  return res.json() as Promise<UserEventStats>;
}

// A user's full profile — identity, overall stats, world rank, and highlights.
export type UserProfile = {
  id: number;
  name: string;
  member_since: number | null;          // unix seconds
  stats: {
    total_picks: number;
    settled: number;
    correct: number;
    winrate: number | null;
  };
  world_rank: { rank: number; total_ranked: number } | null;  // null if unranked
  friends_count: number;
  events_count: number;
  recent_form: string[];                // ["W","W","L",...] most recent first
  current_streak: { type: "win" | "loss"; count: number } | null;
  best_event: {
    event_id: number;
    title: string;
    correct: number;
    of: number;
    winrate: number;
  } | null;
};

export async function getUserProfile(userId: number): Promise<UserProfile> {
  const res = await fetch(`${BASE_URL}/api/users/${userId}/profile`, {
    credentials: "include", // endpoint requires the auth cookie
  });
  if (!res.ok) throw new Error("Could not load profile");
  return res.json() as Promise<UserProfile>;
}

export async function predict(
  fighterA: string,
  fighterB: string,
): Promise<PredictResult> { // the odel is expecting the return type to be PredictResult, that is the promise
  const res = await fetch(`${BASE_URL}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fighter_a: fighterA, fighter_b: fighterB }),
    credentials: "include", //tell the browser to imnclude the cookie
  });
  if (res.status === 402) {
    // free predictions used up — a distinct error so the page can show a paywall
    const err = await res.json().catch(() => ({}));
    throw new PaywallError(err.detail || "You've used your free predictions.");
  }
  if (!res.ok) {
    // FastAPI puts error text in `detail`.
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Prediction failed");
  }
  return res.json() as Promise<PredictResult>;
}

// front end function that calls the backend, 
//backend verifies password and creates token
export async function login(email : string, password : string): Promise<LoginResponse> {
  //fetch from backend, wait for response
  const res = await fetch(`${BASE_URL}/api/login`, {
    method: "POST", //sending to backend server
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email, password: password }),
    credentials: "include", //  accept and   store the httpOnly cookie the server sets
  });
  if (!res.ok) {
    // FastAPI puts error text in `detail`.
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  return res.json() as Promise<LoginResponse>;
  
}
 export async function signup(email : string, password : string): Promise<SignupResponse> {
  //fetch from backend, wait for response
  const res = await fetch(`${BASE_URL}/api/sign_up`, {
    method: "POST", //sending to backend server
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email, password: password }),
  });
  if (!res.ok) {
    // FastAPI puts error text in `detail`.
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Signup failed");
  }
  return res.json() as Promise<SignupResponse>;

}


export async function me(): Promise<MeResponse> {
  const res = await fetch(`${BASE_URL}/api/me`, {
    credentials: "include", // send the cookie so the backend can identify us
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Not authenticated");
  }
  return res.json() as Promise<MeResponse>;
}
// Thrown when an action needs a logged-in user. The UI catches this to redirect to login.
export class AuthError extends Error {}
export class PaywallError extends Error {}   // thrown on 402: free predictions used up

// Create or update the current user's pick for a fight. Needs the auth cookie.
export async function makePick(fightId: number, picked: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/picks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ fight_id: fightId, picked }),
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not save pick");
  }
}

// The current user's picks as { fight_id: picked }. Returns {} when logged out.
export async function getMyPicks(): Promise<Record<number, string>> {
  const res = await fetch(`${BASE_URL}/api/picks/me`, { credentials: "include" });
  if (!res.ok) return {};
  const data: { picks: Record<number, string> } = await res.json();
  return data.picks;
}

// clear the auth cookie server-side
export async function logout(): Promise<void> {
  await fetch(`${BASE_URL}/api/logout`, { method: "POST", credentials: "include" });
}

// One row of the worldwide leaderboard. winrate is null until fights settle.
export type LeaderboardRow = {
  id: number;          // user id — used to send a friend invite from a card
  name: string;
  total_picks: number;
  settled: number;
  correct: number;
  winrate: number | null;
  points: number;      // room score: 10 per correct pick (rooms rank by this)
};

export async function getLeaderboard(): Promise<LeaderboardRow[]> {
  const res = await fetch(`${BASE_URL}/api/leaderboard`);
  if (!res.ok) throw new Error("Could not load leaderboard");
  const data: { leaderboard: LeaderboardRow[] } = await res.json();
  return data.leaderboard;
}

// ---- Friends ----
export type Friend = { id: number; email: string };
export type PendingInvite = { invite_id: number; from: string };

// invite by email (Friends page) or by user_id (from a card)
export async function inviteFriend(body: { email?: string; user_id?: number }): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/friends/invite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (res.status === 401) throw new AuthError("Not authenticated");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not send invite");
  }
}

export async function acceptInvite(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/friends/${id}/accept`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not accept invite");
  }
}

export async function declineInvite(id: number): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/friends/${id}/decline`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Could not decline invite");
  }
}

export async function getFriends(): Promise<Friend[]> {
  const res = await fetch(`${BASE_URL}/api/friends`, { credentials: "include" });
  if (!res.ok) return [];
  const data: { friends: Friend[] } = await res.json();
  return data.friends;
}

export async function getPending(): Promise<PendingInvite[]> {
  const res = await fetch(`${BASE_URL}/api/friends/pending`, { credentials: "include" });
  if (!res.ok) return [];
  const data: { pending: PendingInvite[] } = await res.json();
  return data.pending;
}

export async function getTopCareers(n = 10): Promise<TopCareer[]> {
  const res = await fetch(`${BASE_URL}/api/careers/top?n=${n}`);
  const data = await res.json();
  return data.careers;           // assert the shape via the return type
}