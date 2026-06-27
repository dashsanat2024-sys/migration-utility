/**
 * Arthavi brand mark + optional product label.
 * Logo source: arthavi_logo_image.png
 */
export default function BrandLogo({ size = 44, subtitle, dark = true, className = '' }) {
  const imgHeight = size;
  const imgWidth = Math.round(size * 1.45);
  const titleColor = dark ? '#FFFFFF' : '#1A1A1A';
  const subColor = dark ? 'rgba(255,255,255,0.55)' : '#6B6B6B';

  return (
    <div className={`brand-logo ${className}`.trim()}>
      <img
        src="/arthavi-logo.png"
        alt="Arthavi"
        width={imgWidth}
        height={imgHeight}
        className="brand-logo-img"
      />
      {subtitle !== false && (
        <div className="brand-logo-text">
          <span className="brand-logo-title" style={{ color: titleColor }}>
            Migration Utility
          </span>
          {subtitle && (
            <span className="brand-logo-sub" style={{ color: subColor }}>
              {subtitle}
            </span>
          )}
          {!subtitle && (
            <span className="brand-logo-sub" style={{ color: subColor }}>
              Data migration platform
            </span>
          )}
        </div>
      )}
    </div>
  );
}
