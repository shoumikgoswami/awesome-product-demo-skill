import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
// Optional: point Remotion at a specific Chrome/Chromium if the auto-download is blocked on your network:
// Config.setBrowserExecutable('/path/to/chrome');
