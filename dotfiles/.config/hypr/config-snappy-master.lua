hl.config({
    general = {
        gaps_in = 0,
        gaps_out = 0,
        gaps_workspaces = 0,
        float_gaps = 0,
        border_size = 0,
        col = {
            inactive_border = "rgba(595959aa)",
            active_border = { colors = {"rgba(33ccffee)", "rgba(00ff99ee)"}, angle = 0 },
        },
        resize_on_border = false,
        extend_border_grab_area = 15,
        hover_icon_on_border = true,
        layout = "master",
    },
    decoration = {
        rounding = 0,
        active_opacity = 1.0,
        inactive_opacity = 1.0,
        shadow = {
            enabled = true,
            range = 4,
            render_power = 4,
            scale = 1.0,
            sharp = false,
            color = "rgba(1a1a1aee)",
            offset = { 0, 0 },
        },
        blur = {
            enabled = true,
            size = 3,
            passes = 1,
            vibrancy = 0.0,
            noise = 0.0117,
            contrast = 0.8916,
            brightness = 1.0,
            special = false,
            popups = false,
            xray = false,
            ignore_opacity = true,
            new_optimizations = true,
        },
        dim_inactive = true,
        dim_strength = 0.4,
    },
    master = {
        mfact = 0.69,
        orientation = "left",
        new_on_top = false,
        new_status = "master",
    },
    dwindle = {
        preserve_split = true,
        smart_split = false,
        force_split = 0,
        default_split_ratio = 1.0,
    },
    animations = {
        enabled = true,
    },
    input = {
        follow_mouse = 1,
        sensitivity = 0.0,
        natural_scroll = false,
        repeat_rate = 25,
        repeat_delay = 600,
        kb_layout = "us,bg",
        numlock_by_default = false,
        touchpad = {
            natural_scroll = true,
            tap_to_click = true,
            disable_while_typing = true,
            scroll_factor = 1.0,
        },
    },
    cursor = {
        inactive_timeout = 0.0,
        hide_on_key_press = true,
        warp_on_change_workspace = 0,
    },
    misc = {
        disable_hyprland_logo = false,
        disable_splash_rendering = true,
        animate_manual_resizes = false,
        animate_mouse_windowdragging = false,
        focus_on_activate = false,
    },
})

hl.curve("tune", { type = "bezier", points = { {0.23, 1.0}, {0.32, 1.0} } })
hl.animation({ leaf = "windows", enabled = true, speed = 3.0, bezier = "tune", style = "popin 80%" })

hl.layer_rule({ name = "blur-waybar", match = { namespace = "waybar" }, blur = true })
