
const BASE_URL = "http://localhost:8000";

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
};
export type Phase = {
  fights: number;
  win_rate: number;     
  raw_perf: number;
  adj_perf: number;
  opp_strength: number; 
};
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
export type LoginResponse = { message: string };
export type SignupResponse = { id: number; email: string };
export type MeResponse = { email: string };


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


export async function predict(
  fighterA: string,
  fighterB: string,
): Promise<PredictResult> { // the odel is expecting the return type to be PredictResult, that is the promise
  const res = await fetch(`${BASE_URL}/api/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fighter_a: fighterA, fighter_b: fighterB }),
  });
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