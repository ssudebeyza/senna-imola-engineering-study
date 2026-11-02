"""Senna, Imola 1994: transparent engineering sensitivity study.

This script does not reconstruct or prove the cause of the accident. It
compares a simplified aero/grip model, published steering-tube geometry and an
explicitly idealised steering-disconnection trajectory.
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class VehicleCase:
    """Editable nominal inputs. See README for evidence and assumptions."""

    mass_kg: float = 595.0
    speed_kmh: float = 305.0
    corner_radius_m: float = 250.0
    air_density_kg_m3: float = 1.225
    tyre_mu: float = 1.60
    cla_m2: float = 3.20
    track_half_width_m: float = 7.0
    impact_speed_kmh: float = 210.0

    @property
    def speed_ms(self) -> float:
        return self.speed_kmh / 3.6


CASE = VehicleCase()
G = 9.81


def required_lateral_force(mass_kg, speed_ms, radius_m):
    """Point-mass centripetal force requirement."""
    return mass_kg * speed_ms**2 / radius_m


def downforce(rho, cla_m2, speed_ms):
    """Aerodynamic load from F = 0.5*rho*(CL*A)*v^2."""
    return 0.5 * rho * cla_m2 * speed_ms**2


def available_lateral_force(mass_kg, tyre_mu, aero_load_n):
    """Simplified friction limit with constant effective tyre coefficient."""
    return tyre_mu * (mass_kg * G + aero_load_n)


def grip_margin_percent(available_n, required_n):
    """Positive values indicate surplus force capacity in this model."""
    return 100.0 * (available_n - required_n) / required_n


def critical_aero_loss_percent(case):
    """Solve the fixed-speed force balance exactly for aero loss."""
    fy_required = required_lateral_force(
        case.mass_kg, case.speed_ms, case.corner_radius_m
    )
    nominal_df = downforce(case.air_density_kg_m3, case.cla_m2, case.speed_ms)
    required_df = fy_required / case.tyre_mu - case.mass_kg * G
    loss_fraction = 1.0 - required_df / nominal_df
    return 100.0 * loss_fraction if 0.0 <= loss_fraction <= 1.0 else None


def polar_second_moment_mm4(outer_diameter_mm, wall_mm):
    """Polar second moment of area for a hollow circular tube."""
    inner_diameter_mm = outer_diameter_mm - 2.0 * wall_mm
    return np.pi * (outer_diameter_mm**4 - inner_diameter_mm**4) / 32.0


def steering_section_comparison():
    """Compare the published original and reduced tube dimensions.

    This nominal calculation excludes the weld, material mismatch, surface
    finish, crack geometry, stress concentration and actual load spectrum.
    """
    original_od, original_wall = 22.225, 0.9
    reduced_od, reduced_wall = 18.0, 1.2
    j_original = polar_second_moment_mm4(original_od, original_wall)
    j_reduced = polar_second_moment_mm4(reduced_od, reduced_wall)
    stress_ratio = (reduced_od / 2.0 / j_reduced) / (
        original_od / 2.0 / j_original
    )
    return {
        "j_original_mm4": j_original,
        "j_reduced_mm4": j_reduced,
        "j_reduction_percent": 100.0 * (1.0 - j_reduced / j_original),
        "nominal_stress_increase_percent": 100.0 * (stress_ratio - 1.0),
    }


def idealised_trajectory(case, duration_s=1.0):
    """Compare circular motion with constant-speed tangent motion."""
    time_s = np.linspace(0.0, duration_s, 300)
    distance_m = case.speed_ms * time_s
    angle_rad = distance_m / case.corner_radius_m

    connected_x = case.corner_radius_m * np.sin(angle_rad)
    connected_y = case.corner_radius_m * (1.0 - np.cos(angle_rad))
    tangent_x = distance_m
    tangent_y = np.zeros_like(time_s)
    outward_deviation = (
        np.sqrt(case.corner_radius_m**2 + distance_m**2) - case.corner_radius_m
    )
    time_to_edge = np.sqrt(
        (case.corner_radius_m + case.track_half_width_m) ** 2
        - case.corner_radius_m**2
    ) / case.speed_ms
    return {
        "time_s": time_s,
        "connected_x": connected_x,
        "connected_y": connected_y,
        "tangent_x": tangent_x,
        "tangent_y": tangent_y,
        "outward_deviation": outward_deviation,
        "time_to_edge_s": time_to_edge,
    }


def kinetic_energy_mj(mass_kg, speed_kmh):
    """Translational kinetic energy in megajoules."""
    return 0.5 * mass_kg * (speed_kmh / 3.6) ** 2 / 1e6


def hand_calculation_validation(case):
    """Compare the Python outputs with the rounded preliminary hand study."""
    python_values = {
        "speed_ms": case.speed_ms,
        "lateral_acceleration_ms2": case.speed_ms**2 / case.corner_radius_m,
        "lateral_acceleration_g": case.speed_ms**2 / case.corner_radius_m / G,
        "required_lateral_force_kn": required_lateral_force(
            case.mass_kg, case.speed_ms, case.corner_radius_m
        )
        / 1000.0,
        "critical_aero_loss_percent": critical_aero_loss_percent(case),
    }
    hand_values = {
        "speed_ms": 84.72,
        "lateral_acceleration_ms2": 28.71,
        "lateral_acceleration_g": 2.93,
        "required_lateral_force_kn": 17.08,
        "critical_aero_loss_percent": 65.6,
    }
    return {
        key: {
            "hand": hand_values[key],
            "python": python_values[key],
            "difference": python_values[key] - hand_values[key],
        }
        for key in hand_values
    }


def build_free_body_diagram(case, output_path):
    """Draw the top-view force and trajectory sketch used in the hand study."""
    fig, ax = plt.subplots(figsize=(11, 7))

    radius_plot = 8.0
    theta = np.linspace(-0.35, 1.0, 250)
    centre = np.array([0.0, radius_plot])
    curve_x = radius_plot * np.sin(theta)
    curve_y = radius_plot - radius_plot * np.cos(theta)
    ax.plot(curve_x, curve_y, color="#5f6b73", linewidth=7, alpha=0.28)
    ax.plot(curve_x, curve_y, color="#263238", linewidth=2, label="Circular reference path")

    vehicle = plt.Rectangle(
        (-0.75, -0.38), 1.5, 0.76, facecolor="#f5c518", edgecolor="black", linewidth=1.5
    )
    ax.add_patch(vehicle)
    ax.text(0.0, 0.0, "FW16", ha="center", va="center", fontsize=10, fontweight="bold")

    ax.scatter(*centre, color="#263238", s=55, zorder=5)
    ax.plot([0.0, centre[0]], [0.0, centre[1]], linestyle="--", color="#607d8b")
    ax.text(0.25, radius_plot / 2.0, "R", fontsize=12, color="#455a64")
    ax.text(0.35, radius_plot + 0.15, "Turn centre", fontsize=10, va="bottom")

    ax.arrow(
        0.9,
        -0.65,
        3.4,
        0.0,
        width=0.035,
        head_width=0.28,
        head_length=0.35,
        length_includes_head=True,
        color="#1565c0",
    )
    ax.text(1.5, -1.15, "Velocity, v", color="#1565c0", fontsize=11)
    ax.arrow(
        0.0,
        0.55,
        0.0,
        3.2,
        width=0.035,
        head_width=0.28,
        head_length=0.35,
        length_includes_head=True,
        color="#2e7d32",
    )
    ax.text(
        0.4,
        2.35,
        r"Required lateral force, $F_y=mv^2/R$",
        color="#2e7d32",
        fontsize=11,
        va="center",
    )
    ax.plot(
        [0.0, 8.2],
        [0.0, 0.0],
        color="#c62828",
        linestyle="--",
        linewidth=2.2,
        label="Idealised tangent path after disconnection",
    )
    ax.annotate(
        "No inward steering force\nidealised tangent departure",
        xy=(6.2, 0.0),
        xytext=(5.1, -2.2),
        arrowprops={"arrowstyle": "->", "color": "#c62828"},
        color="#c62828",
        fontsize=10,
        ha="center",
    )

    ax.text(
        -4.4,
        10.3,
        "Top-view free-body and path diagram",
        fontsize=15,
        fontweight="bold",
    )
    ax.text(
        -4.4,
        9.55,
        "Concept developed from the preliminary hand-calculation notes",
        fontsize=10,
        color="#555555",
    )
    ax.set_xlim(-4.5, 9.0)
    ax.set_ylim(-3.5, 10.8)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def build_dashboard(case, output_path):
    """Create the four-panel portfolio figure."""
    plt.style.use(
        "seaborn-v0_8-whitegrid"
        if "seaborn-v0_8-whitegrid" in plt.style.available
        else "default"
    )

    losses_pct = np.linspace(0.0, 100.0, 301)
    fy_required = required_lateral_force(
        case.mass_kg, case.speed_ms, case.corner_radius_m
    )
    aero_series = downforce(
        case.air_density_kg_m3,
        case.cla_m2 * (1.0 - losses_pct / 100.0),
        case.speed_ms,
    )
    fy_available = available_lateral_force(case.mass_kg, case.tyre_mu, aero_series)
    margin = grip_margin_percent(fy_available, fy_required)
    critical_loss = critical_aero_loss_percent(case)

    speeds_kmh = np.linspace(220.0, 330.0, 221)
    map_losses_pct = np.linspace(0.0, 100.0, 201)
    speed_grid_kmh, loss_grid_pct = np.meshgrid(speeds_kmh, map_losses_pct)
    speed_grid_ms = speed_grid_kmh / 3.6
    map_df = downforce(
        case.air_density_kg_m3,
        case.cla_m2 * (1.0 - loss_grid_pct / 100.0),
        speed_grid_ms,
    )
    map_available = available_lateral_force(case.mass_kg, case.tyre_mu, map_df)
    map_required = required_lateral_force(
        case.mass_kg, speed_grid_ms, case.corner_radius_m
    )
    map_margin = grip_margin_percent(map_available, map_required)

    section = steering_section_comparison()
    trajectory = idealised_trajectory(case)

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(
        "Senna, Imola 1994 | Engineering Sensitivity Study",
        fontsize=16,
        fontweight="bold",
    )

    ax = axes[0, 0]
    ax.plot(losses_pct, margin, color="#c62828", linewidth=2.5)
    ax.axhline(0.0, color="black", linewidth=1.5)
    ax.fill_between(
        losses_pct, margin, 0.0, where=margin >= 0.0, color="#2e7d32", alpha=0.22
    )
    ax.fill_between(
        losses_pct, margin, 0.0, where=margin < 0.0, color="#c62828", alpha=0.22
    )
    if critical_loss is not None:
        ax.axvline(critical_loss, color="#ef6c00", linestyle="--", linewidth=2)
        ax.annotate(
            f"Model boundary: {critical_loss:.1f}% loss",
            xy=(critical_loss, 0.0),
            xytext=(critical_loss - 31.0, 18.0),
            arrowprops={"arrowstyle": "->", "color": "#ef6c00"},
            fontsize=9,
        )
    ax.set(
        title="A | Fixed-speed grip margin",
        xlabel="Assumed downforce loss [%]",
        ylabel="Grip margin [%]",
    )

    ax = axes[0, 1]
    contour = ax.contourf(
        speed_grid_kmh,
        loss_grid_pct,
        map_margin,
        levels=np.linspace(-60.0, 100.0, 17),
        cmap="RdYlGn",
        extend="both",
    )
    zero = ax.contour(
        speed_grid_kmh,
        loss_grid_pct,
        map_margin,
        levels=[0.0],
        colors="black",
        linewidths=2,
    )
    ax.clabel(zero, fmt={0.0: "0% margin"}, fontsize=9)
    if critical_loss is not None:
        ax.scatter(
            case.speed_kmh,
            critical_loss,
            color="white",
            edgecolor="black",
            s=65,
            zorder=5,
        )
    ax.set(
        title="B | Speed and aero-loss safety map",
        xlabel="Speed [km/h]",
        ylabel="Assumed downforce loss [%]",
    )
    fig.colorbar(contour, ax=ax, label="Grip margin [%]")

    ax = axes[1, 0]
    labels = ["Original tube\n22.225 x 0.9 mm", "Reduced tube\n18.0 x 1.2 mm"]
    values = [section["j_original_mm4"], section["j_reduced_mm4"]]
    bars = ax.bar(labels, values, color=["#455a64", "#c62828"], width=0.58)
    ax.bar_label(bars, labels=[f"{value:,.0f}" for value in values], padding=4)
    ax.set(
        title="C | Steering-column section comparison",
        ylabel=r"Polar second moment $J$ [mm$^4$]",
    )
    ax.text(
        0.5,
        0.93,
        f"J reduction: {section['j_reduction_percent']:.1f}% | "
        f"Nominal stress increase: "
        f"{section['nominal_stress_increase_percent']:.1f}%",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
    )

    ax = axes[1, 1]
    ax.plot(
        trajectory["connected_x"],
        trajectory["connected_y"],
        color="#1565c0",
        linewidth=2.5,
        label="Circular reference path",
    )
    ax.plot(
        trajectory["tangent_x"],
        trajectory["tangent_y"],
        color="#c62828",
        linewidth=2.5,
        label="Idealised tangent path",
    )
    edge_t = float(trajectory["time_to_edge_s"])
    edge_x = case.speed_ms * edge_t
    ax.scatter(edge_x, 0.0, color="#c62828", s=55, zorder=4)
    ax.annotate(
        f"Assumed 7 m edge: {edge_t:.2f} s",
        xy=(edge_x, 0.0),
        xytext=(edge_x - 17.0, 6.0),
        arrowprops={"arrowstyle": "->", "color": "#c62828"},
        fontsize=9,
    )
    ax.set_aspect("equal", adjustable="box")
    ax.set(
        title="D | Idealised path after steering disconnection",
        xlabel="Longitudinal position [m]",
        ylabel="Lateral position [m]",
    )
    ax.legend(fontsize=9)

    fig.text(
        0.5,
        0.012,
        "Sensitivity model only. It does not reconstruct or determine the accident cause.",
        ha="center",
        fontsize=10,
        color="#555555",
    )
    fig.tight_layout(rect=[0.0, 0.035, 1.0, 0.96])
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def print_summary(case):
    """Print traceable headline outputs."""
    critical_loss = critical_aero_loss_percent(case)
    section = steering_section_comparison()
    trajectory = idealised_trajectory(case)
    entry_energy = kinetic_energy_mj(case.mass_kg, case.speed_kmh)
    impact_energy = kinetic_energy_mj(case.mass_kg, case.impact_speed_kmh)
    validation = hand_calculation_validation(case)

    print("\nSENNA / IMOLA 1994: ENGINEERING SENSITIVITY SUMMARY")
    print("=" * 58)
    print(
        f"Required lateral acceleration: "
        f"{case.speed_ms**2 / case.corner_radius_m / G:.2f} g"
    )
    if critical_loss is None:
        print("No 0-100% aero-loss boundary exists for the nominal inputs.")
    else:
        print(
            f"Nominal fixed-speed model boundary: "
            f"{critical_loss:.1f}% downforce loss"
        )
    print(f"Steering-tube J reduction: {section['j_reduction_percent']:.1f}%")
    print(
        f"Nominal same-torque stress increase: "
        f"{section['nominal_stress_increase_percent']:.1f}%"
    )
    print(
        f"Idealised time to 7 m outward deviation: "
        f"{trajectory['time_to_edge_s']:.2f} s"
    )
    print(f"Kinetic energy at {case.speed_kmh:.0f} km/h: {entry_energy:.2f} MJ")
    print(
        f"Kinetic energy at {case.impact_speed_kmh:.0f} km/h: "
        f"{impact_energy:.2f} MJ"
    )
    print(
        f"Energy reduction between those speeds: "
        f"{100.0 * (1.0 - impact_energy / entry_energy):.1f}%"
    )
    maximum_difference = max(abs(item["difference"]) for item in validation.values())
    print(f"Maximum rounded hand/Python difference: {maximum_difference:.3f}")
    print("\nThese are model outputs, not findings of accident causation.")


if __name__ == "__main__":
    dashboard_output = Path(__file__).with_name("senna_engineering_dashboard.png")
    diagram_output = Path(__file__).with_name("senna_free_body_diagram.png")
    build_dashboard(CASE, dashboard_output)
    build_free_body_diagram(CASE, diagram_output)
    print_summary(CASE)
    print(f"\nDashboard saved to: {dashboard_output}")
    print(f"Free-body diagram saved to: {diagram_output}")