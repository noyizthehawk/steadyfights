
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
  // Tale of the tape: each fighter's actual value on a key stat with who it favors.
  factors: {
    label: string;
    value_a: string;
    value_b: string;
    favors: string;
  }[];
};


export type LoginResponse = { message: string };
export type SignupResponse = { id: number; email: string };
export type MeResponse = { email: string };



// Fetch the list of fighter names for the dropdowns.
export async function getFighters(): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/api/fighters`);
  if (!res.ok) throw new Error("Could not load fighters");
  const data: { fighters: string[] } = await res.json();
  return data.fighters;
}

// Ask the model to predict a matchup. The return type tells callers exactly
// when called in the front end. the backend returns the prediction
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

// "Who am I?" The frontend asks the backend who the cookie belongs to.
// get_current_user
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