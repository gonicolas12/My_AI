/*
 * Logo de My_AI : le robot 🤖 que l'interface Tk dessinait en orange uni.
 * Tracé repris de vscode_extension/media/icon-activitybar.svg ; couleur
 * héritée (currentColor), en --accent par défaut.
 */

interface RobotLogoProps {
  size?: number;
  className?: string;
  title?: string;
}

export function RobotLogo({ size = 24, className, title }: RobotLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
      role={title ? 'img' : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <circle cx="7" cy="1.5" r="1" />
      <rect x="6.6" y="2.4" width="0.8" height="2.8" rx="0.4" />
      <circle cx="17" cy="1.5" r="1" />
      <rect x="16.6" y="2.4" width="0.8" height="2.8" rx="0.4" />
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M 5 4.5 H 19 A 4 4 0 0 1 23 8.5 V 18 A 4 4 0 0 1 19 22 H 5 A 4 4 0 0 1 1 18 V 8.5 A 4 4 0 0 1 5 4.5 Z M 6.25 9.25 H 8.75 A 1.25 1.25 0 0 1 10 10.5 V 12 A 1.25 1.25 0 0 1 8.75 13.25 H 6.25 A 1.25 1.25 0 0 1 5 12 V 10.5 A 1.25 1.25 0 0 1 6.25 9.25 Z M 15.25 9.25 H 17.75 A 1.25 1.25 0 0 1 19 10.5 V 12 A 1.25 1.25 0 0 1 17.75 13.25 H 15.25 A 1.25 1.25 0 0 1 14 12 V 10.5 A 1.25 1.25 0 0 1 15.25 9.25 Z M 9 15.75 H 15 A 1 1 0 0 1 15 17.75 H 9 A 1 1 0 0 1 9 15.75 Z"
      />
    </svg>
  );
}
