import { useState } from "react";
export default function CreateProjectForm({ onSubmit }) {
  const [name,setName]=useState("");
  return <form className="inline-form" onSubmit={async event => { event.preventDefault(); await onSubmit(name); setName(""); }}><input value={name} onChange={event=>setName(event.target.value)} placeholder="New project name" required/><button>Create project</button></form>;
}
