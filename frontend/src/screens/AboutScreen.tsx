import { BackButton } from "../components/BackButton";
import common from "../styles/common.module.css";
import s from "./AboutScreen.module.css";

/*
 * Privacy, terms, and data-source credits. Static content, reachable from the You tab. Covers the
 * beta's data handling (location + photo EXIF GPS, on-device profile, no accounts) and carries the
 * attribution the open data sources require - OpenStreetMap (ODbL) most importantly, plus eBird,
 * NWS/USGS, BirdNET, and TomTom.
 */

export function AboutScreen() {
  return (
    <div className={common.screen}>
      <div className={common.scrollArea}>
        <div className={s.backRow}>
          <BackButton bg="rgba(45,59,45,0.1)" stroke="var(--forest)" blur={false} />
        </div>
        <div className={common.eyebrow}>MTBIRB</div>
        <div className={common.title}>Privacy &amp; credits</div>

        <p className={s.note}>
          MTBirb is an early beta. It has no accounts and shows no ads. Trail difficulty,
          conditions, and wildlife odds are estimates from public data, not guarantees — ride
          within your limits and check local rules and trail status.
        </p>

        <div className={common.sectionLabel}>YOUR DATA</div>
        <ul className={s.list}>
          <li>
            <b>Location</b> is used to find trails near you. Your coordinates are sent to the server
            only to look up nearby trails, wildlife, and weather — they aren't tied to an identity
            or kept as a history.
          </li>
          <li>
            <b>Photos</b> you attach to a ride are read on your device; only a small thumbnail and
            the photo's GPS coordinates are kept, to place it on the trail. A hero photo you set for
            a trail is stored on the server and shared for that trail. Don't upload a photo whose
            location you'd rather keep private.
          </li>
          <li>
            <b>Your profile, favorite trails, and bird wishlist</b> stay in this browser
            (localStorage) on this device only — they're never sent to us.
          </li>
          <li>No third-party tracking or analytics.</li>
        </ul>

        <div className={common.sectionLabel}>TERMS</div>
        <ul className={s.list}>
          <li>
            Provided as-is, with no warranty. This is a beta — features and data may change, and
            data may be lost.
          </li>
          <li>
            Use it responsibly: don't rely on it for safety-critical decisions, and don't abuse the
            service or the underlying data sources.
          </li>
        </ul>

        <div className={common.sectionLabel}>DATA &amp; CREDITS</div>
        <ul className={s.list}>
          <li>
            Trail geometry &amp; map data ©{" "}
            <a className={s.link} href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
              OpenStreetMap
            </a>{" "}
            contributors, licensed under the{" "}
            <a className={s.link} href="https://opendatacommons.org/licenses/odbl/" target="_blank" rel="noreferrer">
              ODbL
            </a>
            .
          </li>
          <li>
            Wildlife observations from{" "}
            <a className={s.link} href="https://ebird.org" target="_blank" rel="noreferrer">
              eBird
            </a>
            , Cornell Lab of Ornithology.
          </li>
          <li>
            Weather from the US{" "}
            <a className={s.link} href="https://www.weather.gov" target="_blank" rel="noreferrer">
              National Weather Service
            </a>{" "}
            (NOAA); elevation from USGS 3DEP and{" "}
            <a className={s.link} href="https://open-meteo.com" target="_blank" rel="noreferrer">
              Open-Meteo
            </a>
            .
          </li>
          <li>
            Bird sound ID by{" "}
            <a className={s.link} href="https://birdnet.cornell.edu" target="_blank" rel="noreferrer">
              BirdNET
            </a>{" "}
            (Cornell Lab / Chemnitz University).
          </li>
          <li>Maps &amp; driving routes © TomTom.</li>
        </ul>

        <p className={s.footer}>MTBirb is open source under the GPLv3.</p>
      </div>
    </div>
  );
}
