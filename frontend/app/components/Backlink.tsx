// Import necessary types from React
"use client";
import { useRouter } from "next/navigation";
import React, { MouseEvent, AnchorHTMLAttributes } from "react";

// Define an interface for the component props
// Extend AnchorHTMLAttributes to include all standard <a> attributes
interface BackLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  children: React.ReactNode; // Ensure children is of type ReactNode
}

// Define the BackLink component with the props type
const BackLink: React.FC<BackLinkProps> = ({ children, ...props }) => {
  const router = useRouter(); // Get the router instance

  // Define the click handler with the correct event type
  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault(); // Prevent the default link behavior
    router.back(); // Navigate back to the previous page
  };

  // Return the anchor element with the click handler and spread the props
  return (
    <a href="#" onClick={handleClick} {...props}>
      {children}
    </a>
  );
};

export default BackLink;
