# Recovered baseline theta formula

## Update: user-confirmed equation image recovered from browser history

The August 5, 2025 conversation "Updated theory summary" (a private chat; link removed) contains an uploaded equation image followed by the user's statement "thats the equation". The image was opened and visually inspected on 2026-09-09. It reads:

    theta = (1 + ln(S_actual/S_reference))
            * (1 + sqrt(ln(T_reference/T_actual)))
            * (1 + sqrt(ln(E_demanded/E_available)))

The image also gives g_adjusted = g_Newtonian * exp(-|theta-1|).

Crucial distinctions: the temperature ratio is REFERENCE / ACTUAL, and there are no adjustable weights or exponents in this image. It is a stronger source for the user's intended equation at that date than the assistant's preceding summary. That summary instead wrote exp(ln(r_S)+2 ln(T_actual/T_reference)+2 ln(r_E)), which is not equivalent. The later Theory 1 formula below also has a different temperature orientation and adds weights/powers. Preserve these as separate historical versions.

For positive inputs, the image's real-valued domain requires T_actual <= T_reference and E_demanded >= E_available. The entropy factor may become negative if S_actual/S_reference < exp(-1). All baseline ratios equal to 1 give theta=1. Handling outside this domain is still not specified in the recovered image. Temperature comparisons require an absolute temperature scale for a physical interpretation.

This is the earliest user-confirmed thermodynamic equation located in this search, not a claim that no earlier version exists. The June fluid work uses theta without establishing that this August thermodynamic definition was already its scalar closure.

## Later Theory 1 form

Recovered 2026-09-09 from `companion/library/Shovelcat_Theory_1.pdf`, Appendix B.3, printed page 42. The rendered page was inspected to verify exponent placement and square-root scope. This is the paper's near-equilibrium planetary application; it is not yet confirmed as the earliest browser-chat version.

Define r_S = S_act/S_ref, r_T = T_act/T_ref, r_E = E_dem/E_av. The printed formula is:

    theta = (1 + w_S ln[r_S^p_S])
            (1 + w_T sqrt(ln[r_T^p_T]))
            (1 + w_E sqrt(ln[r_E^p_E])).

S denotes the entropy-related input, T temperature, and E energy demand relative to available energy. All ratios are dimensionless. At r_S=r_T=r_E=1 the formula gives theta=1.

The page assigns application-specific proxies: compositional/thermal variance for r_S, blackbody equilibrium temperature relative to a monthly mean for r_T, and kinetic/tidal energy densities relative to a gravitational binding energy density scale for r_E. These are the source's modeling choices, not independently validated thermodynamic identifications.

The paper does not provide numerical weights and exponents in Appendix B, but Table 1 on printed page 37 ("Fixed analysis parameters (preregistered)") lists (w_S,w_T,w_E)=(0.8,0.6,0.4) and (p_S,p_T,p_E)=(1.2,1.0,0.8). [Found 2026-09-13; see THETA_KINETIC_RESULTS.md.] It refers to the earlier planetary analysis (Earth-like setting). Equation 12 on page 14 is another presentation; Appendix B.3 explicitly places the exponents inside the logarithms and is the transcription used above.

## Separate later version

`companion/library/OBSERVER_NETWORK_THEORY.md`, lines 55–62, gives an additive formula, theta=w_S theta_S+w_T theta_T+w_E theta_E, with w_T=1/2, w_E=1/(2 phi), w_S=1/(2 phi^2). These values cannot yet be assigned to the multiplicative Theory 1 formula as original parameters. Its component transformations and exponents are not supplied by that passage.

## Unresolved before a faithful fluid test

1. Recover the numerical weights and powers from the earlier planetary analysis or browser conversations.
2. Recover the treatment of below-baseline ratios. For positive powers, r_T<1 or r_E<1 makes the corresponding logarithm negative and its square root non-real. Clamping, absolute values, signed roots, or complex values would each be a different model; none should be silently substituted.
3. Fix the physical definition and reference state of entropy, temperature, and energy for the chosen fluid. The existing isothermal vorticity experiment does not evolve temperature or thermodynamic entropy, so these inputs cannot simply be read from it.
4. Recover the actual momentum-equation modification, if any. A diagnostic alone does not specify a coupling to Navier-Stokes.

The first experiment tested theta_E=P/D, a newly proposed energy-balance diagnostic. Its negative threshold findings do not test this recovered multiplicative formula.

## Search status

The uniquely numbered theory PDFs were searched for the ratio notation and reference to planetary analysis; no additional match was found outside Theory 1. Targeted source-code and text searches found the separate later additive definition. Alternate PDF copies and historical transcripts are not exhaustively audited.

After the user signed in, browser history was searched and the user-confirmed image above was recovered. Additional historical equations and source limitations are recorded in BROWSER_RECOVERY.md.
