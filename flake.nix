{
  description = "chorebox — personal CLI for everyday chores";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        chorebox = pkgs.python3Packages.buildPythonApplication {
          pname = "chorebox";
          version = "0.1.0";
          src = ./.;
          pyproject = true;
          build-system = [ pkgs.python3Packages.setuptools ];
          dependencies = with pkgs.python3Packages; [
            yt-dlp
            rich
            questionary
            pikepdf
          ];
          nativeCheckInputs = [ pkgs.python3Packages.pytestCheckHook ];

          # ffmpeg is a runtime dependency (subprocess/yt-dlp postprocessing),
          # not an import — wrap it onto PATH so chorebox is self-contained
          # and doesn't depend on the consuming machine's own config for it.
          nativeBuildInputs = [ pkgs.makeWrapper ];
          postFixup = ''
            wrapProgram $out/bin/chorebox --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.ffmpeg-full ]}
          '';

          meta = with pkgs.lib; {
            description = "Personal CLI for everyday chores — video trimming, transcripts, PDF cleanup, file conversion";
            homepage = "https://github.com/vigneshgarrapally/chorebox";
            license = licenses.mit;
            mainProgram = "chorebox";
          };
        };
      in
      {
        packages.default = chorebox;
        apps.default = flake-utils.lib.mkApp { drv = chorebox; };
        devShells.default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (ps: with ps; [ yt-dlp rich questionary pikepdf pytest ]))
            pkgs.ffmpeg-full
            pkgs.ruff
          ];
        };
      });
}
