import { RobotLogo } from '../../components/ui/RobotLogo';
import { Composer } from './Composer';

/** Écran d'accueil : logo, titre « My_AI », zone de saisie centrée (_create_home_screen) */
export function HomeScreen() {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-y-auto px-6 pb-[12vh]">
      <div
        className="flex w-full flex-col items-center"
        style={{ animation: 'rise-in var(--motion) var(--motion-ease)' }}
      >
        <RobotLogo size={84} className="text-accent" title="My_AI" />
        <h1 className="mt-5 mb-9 text-display leading-none font-bold tracking-tight text-fg">
          My_AI
        </h1>
        <Composer variant="home" />
      </div>
    </div>
  );
}
