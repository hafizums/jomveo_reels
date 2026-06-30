export default function ErrorBanner({message}) { return message?<div className="error-banner" role="alert">{message}</div>:null; }
