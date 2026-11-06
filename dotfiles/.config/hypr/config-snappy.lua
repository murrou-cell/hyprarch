hl.config({
    general = {
        gaps_in = 0,
        gaps_out = 0,
        border_size = 0,
        col = { active_border = { colors = {"rgba(33ccffee)", "rgba(00ff99ee)"}, angle = 0 } },
        layout = "master",
    },
    decoration = {
        rounding = 0,
        active_opacity = 1.0,
        inactive_opacity = 1.0,
        dim_inactive = true, dim_strength = 0.4,
        shadow = { enabled = true, range = 4, render_power = 4 },
        blur = { enabled = true, size = 3, passes = 1, vibrancy = 0.0 },
    },
    animations = { enabled = true },
})

hl.curve("tune", { type = "bezier", points = { {0.23, 1.0}, {0.32, 1.0} } })
hl.animation({ leaf = "windows", enabled = true, speed = 3.0, bezier = "tune", style = "popin 80%" })

hl.layer_rule({ name = "blur-waybar", match = { namespace = "waybar" }, blur = true })
