
const BASE_URL = "http://localhost:8000";

// The exact shape of what /api/predict returns. This is the TypeScript payoff:
// every component that uses a prediction now KNOWS these fields (autocomplete +
// compile-time errors), instead of guessing at runtime.
export type PredictResult = {
  fighter_a: string;
  fighter_b: string;
  style_a: string;
  style_b: string;
  prob_a: number;
  prob_b: number;
  pick: string;
  confidence: number;
};
export type LoginResponse = { access_token: string; token_type: string }; //
export type SignupResponse = { id: string; email: string };



// Fetch the list of fighter names for the dropdowns.
export async function getFighters(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/api/fighters`);
  if (!res.ok) throw new Error("Could not load fighters");
  const data: { fighters: string[] } = await res.json();
  return data.fighters;
}

// Ask the model to predict a matchup. The return type tells callers exactly
export async function predict(
  fighterA: string,
  fighterB: string,
): Promise<PredictResult> {
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
  });
  if (!res.ok) {
    // FastAPI puts error text in `detail`.
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  return res.json() as Promise<LoginResponse>;
  
}
 export async function signup(email : number, password : string): Promise<SignupResponse> {
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