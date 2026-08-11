"use client";

import React from "react";

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="skeleton-line title" />
      <div className="skeleton-line meta" />
      <div className="skeleton-badge-row">
        <div className="skeleton-badge" />
        <div className="skeleton-badge" />
      </div>
      <div className="skeleton-bar" />
    </div>
  );
}

export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="cards-grid">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonDetail() {
  return (
    <div className="skeleton-detail-container">
      <div className="skeleton-header">
        <div className="skeleton-line title" style={{ width: "60%", height: 32 }} />
        <div className="skeleton-line meta" style={{ width: "35%", height: 18 }} />
      </div>
      <div className="skeleton-two-col">
        <div className="skeleton-box" style={{ height: 260 }} />
        <div className="skeleton-box" style={{ height: 260 }} />
      </div>
      <div className="skeleton-box" style={{ height: 180, marginTop: 20 }} />
    </div>
  );
}
