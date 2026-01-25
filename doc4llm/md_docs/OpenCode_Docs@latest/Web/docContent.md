# Web

> **原文链接**: https://opencode.ai/docs/web/

---

# Web

Using OpenCode in your browser.

OpenCode can run as a web application in your browser, providing the same powerful AI coding experience without needing a terminal.

![OpenCode Web - New Session](https://opencode.ai/docs/_astro/web-homepage-new-session.BB1mEdgo_Z1AT1v3.webp)

## Getting Started

Start the web interface by running:

Terminal window
    
    
    opencode web

This starts a local server on `127.0.0.1` with a random available port and automatically opens OpenCode in your default browser.

* * *

## Configuration

You can configure the web server using command line flags or in your [config file](https://opencode.ai/docs/config).

### Port

By default, OpenCode picks an available port. You can specify a port:

Terminal window
    
    
    opencode web --port 4096

### Hostname

By default, the server binds to `127.0.0.1` (localhost only). To make OpenCode accessible on your network:

Terminal window
    
    
    opencode web --hostname 0.0.0.0

When using `0.0.0.0`, OpenCode will display both local and network addresses:
    
    
      Local access:       http://localhost:4096
    
      Network access:     http://192.168.1.100:4096

### mDNS Discovery

Enable mDNS to make your server discoverable on the local network:

Terminal window
    
    
    opencode web --mdns

This automatically sets the hostname to `0.0.0.0` and advertises the server as `opencode.local`.

### CORS

To allow additional domains for CORS (useful for custom frontends):

Terminal window
    
    
    opencode web --cors https://example.com

### Authentication

To protect access, set a password using the `OPENCODE_SERVER_PASSWORD` environment variable:

Terminal window
    
    
    OPENCODE_SERVER_PASSWORD=secret opencode web

The username defaults to `opencode` but can be changed with `OPENCODE_SERVER_USERNAME`.

* * *

## Using the Web Interface

Once started, the web interface provides access to your OpenCode sessions.

### Sessions

View and manage your sessions from the homepage. You can see active sessions and start new ones.

![OpenCode Web - Active Session](https://opencode.ai/docs/_astro/web-homepage-active-session.BbK4Ph6e_Z1O7nO1.webp)

### Server Status

Click “See Servers” to view connected servers and their status.

![OpenCode Web - See Servers](https://opencode.ai/docs/_astro/web-homepage-see-servers.BpCOef2l_ZB0rJd.webp)

* * *

## Attaching a Terminal

You can attach a terminal TUI to a running web server:

Terminal window
    
    
    # Start the web server
    
    opencode web --port 4096
    
    
    
    
    # In another terminal, attach the TUI
    
    opencode attach http://localhost:4096

This allows you to use both the web interface and terminal simultaneously, sharing the same sessions and state.

* * *

## Config File

You can also configure server settings in your `opencode.json` config file:
    
    
    {
    
      "server": {
    
        "port": 4096,
    
        "hostname": "0.0.0.0",
    
        "mdns": true,
    
        "cors": ["https://example.com"]
    
      }
    
    }

Command line flags take precedence over config file settings.
