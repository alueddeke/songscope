import React from "react";

export default function page({ params }: { params: { id: string } }) {
  return <div>logged in user. User ID: {params.id}</div>;
}
