import React from "react";
import BackLink from "@/app/components/Backlink";

export default function page({ params }: { params: { id: string } }) {
  return (
    <div>
      <h1>logged in user. User ID: {params.id}</h1>
      <BackLink>Back</BackLink>
    </div>
  );
}
