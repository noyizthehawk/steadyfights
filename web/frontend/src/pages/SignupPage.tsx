import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { signup } from "../api";
import { errorMessage } from "../lib/errorMessage";

export default function SignupPage(){
     const [email, setEmail] = useState<string>("");
     const [password, setPassword] = useState<string>("");
     const [error, setError] = useState<string>("");

     const navigate = useNavigate();
    
     const handleSignup = async (e: React.FormEvent) => { // event handler handle signn up
        e.preventDefault(); // stop the browser's default full-page form submit
        setError("");
        // try to signn up
        try {
          await signup(email, password); // 
          navigate("/login"); 
        } catch (e: unknown) {
          setError(errorMessage(e));
        }
        
     };
     return (

        <div className="SignupPage page">
          <h2>Sign up</h2>
          <form onSubmit={handleSignup}>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button type="submit">Sign up</button>
          </form>
          {error && <p>{error}</p>}
        </div>
     )





}