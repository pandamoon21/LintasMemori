import { useCallback, useEffect, useState } from "react";

export type DrawerKey = "setup" | "upload" | "pipeline" | "advanced" | null;

export function useDrawers(defaultDrawer: DrawerKey = null) {
  const [openDrawer, setOpenDrawer] = useState<DrawerKey>(defaultDrawer);

  const toggleDrawer = useCallback((drawer: Exclude<DrawerKey, null>) => {
    setOpenDrawer((current) => (current === drawer ? null : drawer));
  }, []);

  const closeDrawer = useCallback(() => {
    setOpenDrawer(null);
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenDrawer(null);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return {
    openDrawer,
    toggleDrawer,
    closeDrawer,
  };
}
