import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

/*
 * The rider's per-device profile + their saved favorites and bird wishlist, persisted to
 * localStorage. With no accounts, each device is one user's data - the simplest multi-user model
 * that still ships; a future accounts layer could sync these to the backend. The logged-birds
 * catalogue (You tab) is NOT here - it's derived from the backend trips (useTrips).
 */

export interface Profile {
  name: string;
  firstName: string;
  photo: string | null; // downscaled data-URL, or null for the initial fallback
}

export interface FavoriteTrail {
  id: string; // catalog external id
  name: string;
  difficulty: string | null;
  miles: number | null;
}

export interface WishlistBird {
  code: string;
  name: string;
}

interface ProfileState {
  profile: Profile | null;
  saveProfile: (name: string, photo: string | null) => void;

  favorites: FavoriteTrail[];
  isFavorite: (id: string) => boolean;
  toggleFavorite: (trail: FavoriteTrail) => void;

  wishlist: WishlistBird[];
  isWishlisted: (code: string) => boolean;
  toggleWishlist: (bird: WishlistBird) => void;
}

const KEY_PROFILE = "mtbirb.profile";
const KEY_FAVORITES = "mtbirb.favorites";
const KEY_WISHLIST = "mtbirb.wishlist";

function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage full / unavailable - the in-memory state still works for this session.
  }
}

const Ctx = createContext<ProfileState | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(() => load<Profile | null>(KEY_PROFILE, null));
  const [favorites, setFavorites] = useState<FavoriteTrail[]>(() => load<FavoriteTrail[]>(KEY_FAVORITES, []));
  const [wishlist, setWishlist] = useState<WishlistBird[]>(() => load<WishlistBird[]>(KEY_WISHLIST, []));

  const saveProfile = useCallback((name: string, photo: string | null) => {
    const trimmed = name.trim();
    const next: Profile = { name: trimmed, firstName: trimmed.split(/\s+/)[0] || trimmed, photo };
    setProfile(next);
    save(KEY_PROFILE, next);
  }, []);

  const toggleFavorite = useCallback((trail: FavoriteTrail) => {
    setFavorites((prev) => {
      const next = prev.some((t) => t.id === trail.id)
        ? prev.filter((t) => t.id !== trail.id)
        : [trail, ...prev];
      save(KEY_FAVORITES, next);
      return next;
    });
  }, []);

  const toggleWishlist = useCallback((bird: WishlistBird) => {
    setWishlist((prev) => {
      const next = prev.some((b) => b.code === bird.code)
        ? prev.filter((b) => b.code !== bird.code)
        : [bird, ...prev];
      save(KEY_WISHLIST, next);
      return next;
    });
  }, []);

  const value = useMemo<ProfileState>(
    () => ({
      profile,
      saveProfile,
      favorites,
      isFavorite: (id) => favorites.some((t) => t.id === id),
      toggleFavorite,
      wishlist,
      isWishlisted: (code) => wishlist.some((b) => b.code === code),
      toggleWishlist,
    }),
    [profile, saveProfile, favorites, toggleFavorite, wishlist, toggleWishlist],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useProfile(): ProfileState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useProfile must be used within ProfileProvider");
  return ctx;
}
