// Two MMA gloves touching, looping - the site's loading indicator
// everywhere a spinner/progress-bar would otherwise go. Deliberately a
// simplified/flat-graphic shape (not photorealistic, no UFC branding -
// the red/blue wrist-wrap is the generic corner-color convention, not a
// trademarked mark) rather than an embedded photo/video asset, so it's
// fully theme-matched and carries no licensing question.
function Glove({ cuffColor, cuffShadow }) {
  return (
    <svg className="glove-svg" viewBox="0 0 130 90" xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="26" width="28" height="38" rx="5" fill={cuffColor} />
      <rect x="6" y="30" width="12" height="30" rx="3" fill={cuffShadow} />
      <ellipse cx="38" cy="20" rx="15" ry="10" fill="#1c1c1c" transform="rotate(-30 38 20)" />
      <path
        d="M22 22 C22 14 30 10 42 10 L70 10 C100 10 118 26 118 46 C118 66 100 80 72 80 L40 80 C28 80 22 74 22 66 Z"
        fill="#232323"
      />
      <path d="M76 20 Q96 46 76 72" fill="none" stroke="#000000" strokeOpacity="0.3" strokeWidth="3" strokeLinecap="round" />
      <ellipse cx="58" cy="26" rx="20" ry="8" fill="#ffffff" opacity="0.07" />
    </svg>
  );
}

export default function GloveLoader({ label = "Loading", size = "md" }) {
  return (
    <div className={`glove-loader glove-loader-${size}`}>
      <div className="glove-loader-stage">
        <div className="glove glove-left"><Glove cuffColor="#3d8bff" cuffShadow="#2a63bd" /></div>
        <div className="glove-flash" />
        <div className="glove glove-right"><Glove cuffColor="#ff4433" cuffShadow="#c22e21" /></div>
      </div>
      {label && (
        <div className="glove-loader-label">
          {label}<span className="glove-loader-dots" />
        </div>
      )}
    </div>
  );
}
