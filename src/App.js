import "./App.css";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
} from "react-router-dom";
import Home from "./pages/Home";
import MyForm from "./pages/Main.js";
import { useAuthenticator, withAuthenticator } from "@aws-amplify/ui-react";

function App() {
  const { signOut } = useAuthenticator();

  return (
    <div className="App">
      <header className="App-header">
        <Router>
          <div className="content-menu-bar">
            <NavLink
              className="content-menu-bar"
              exact
              activeClassName="active"
              to="/"
            >
              Home
            </NavLink>
            <NavLink
              className="content-menu-bar"
              activeClassName="active"
              to="/Main"
            >
              Main
            </NavLink>
          </div>
          <Routes>
            <Route path="/" element={<Home />}></Route>
            <Route path="/Main" element={<MyForm />}></Route>
          </Routes>
        </Router>

        <button onClick={() => signOut()}>Log Out</button>
      </header>
    </div>
  );
}

export default withAuthenticator(App, { hideSignUp: true });
