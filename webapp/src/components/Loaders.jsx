export function DropLoader() {
  return (
    <div className="drop-loader" role="status" aria-label="Yuklanmoqda">
      <svg width="28" height="34" viewBox="0 0 28 34" fill="none">
        <path
          d="M14 0C14 0 26 15.5 26 22.5C26 29.4 20.6 34 14 34C7.4 34 2 29.4 2 22.5C2 15.5 14 0 14 0Z"
          fill="#0EA5E9"
        />
      </svg>
    </div>
  );
}

export function SkeletonCatalog() {
  return (
    <div className="catalog-grid">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="product-card">
          <div className="skeleton" style={{ aspectRatio: "1 / 1" }} />
          <div className="body">
            <div className="skeleton" style={{ height: 14, width: "70%" }} />
            <div className="skeleton" style={{ height: 14, width: "40%" }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonList({ rows = 4 }) {
  return (
    <div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="shop-card">
          <div className="skeleton" style={{ width: 52, height: 52, borderRadius: 10 }} />
          <div style={{ flex: 1 }}>
            <div className="skeleton" style={{ height: 12, width: "60%", marginBottom: 6 }} />
            <div className="skeleton" style={{ height: 12, width: "40%" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
