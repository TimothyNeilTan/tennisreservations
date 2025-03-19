{pkgs}: {
  deps = [
    pkgs.geckodriver
    pkgs.cairo
    pkgs.pango
    pkgs.xorg.libXfixes
    pkgs.xorg.libXdamage
    pkgs.xorg.libXcomposite
    pkgs.at-spi2-core
    pkgs.alsa-lib
    pkgs.nss
    pkgs.gtk3
    pkgs.xorg.libX11
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.postgresql
    pkgs.openssl
  ];
}
