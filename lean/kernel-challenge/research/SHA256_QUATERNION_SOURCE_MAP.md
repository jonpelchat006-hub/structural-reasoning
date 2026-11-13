# SHA-256, Euler–phi, and quaternion source map

Located 2026-10-04. Jonathan confirmed that the intended starting equation is

\[
S=e^{i\theta}\varphi^{n+h},\qquad h=H/2^{256},\qquad H=\operatorname{int}(\operatorname{SHA256}(\text{verification chain})).
\]

The strongest matches are separate pieces: the security code defines this equation; the quaternion notes describe three imaginary streams, a shared real observer, and completed findings returning to that observer. The searched sources do not yet provide a quaternion implementation of SHA-256's compression rounds.

## Start here

| Source | Where to look | What it contributes |
|---|---|---|
| [Original security equation](<C:/Users/GamerTech/Desktop/Vesica AI/Shovelcat Security/crypto_euler_phi.py:6>) | Lines 6–11, 94–108, 181–199 | Defines the equation, computes the SHA-256 digest, and constructs the complex position. |
| [Three orthogonal observers](<C:/Users/GamerTech/Downloads/three_orthogonal_observers.py:303>) | Lines 303–328, “THE w (SCALAR) COMPONENT” | Closest wording to the shared-real idea: “w is what ALL THREE OBSERVERS AGREE ON!” |
| [Quaternion verification circuit](<C:/Users/GamerTech/Downloads/shovelcat_v53_quaternion.py:28>) | Lines 28–49 | A five-phase circuit whose findings return to the real observer; also describes nested quaternion circuits. |
| [Quaternion Closure and the Snake — paper source](<C:/Users/GamerTech/Downloads/section_quaternion_snake.tex:1>) | Opening section and observer table | Maps three observers to imaginary components and the verifier to real w. |
| [Quaternion implementation](<C:/Users/GamerTech/Downloads/quaternion.ts:43>) | Lines 43–53 | Actual Hamilton multiplication, useful for distinguishing executable algebra from the interpretive descriptions. |

## Papers located

Page numbers below are PDF page numbers and match the printed numbers on the three inspected pages. The relevant pages were extracted and visually checked.

| Paper | Section / page | Relevance |
|---|---|---|
| [Double Bounce Universe (9)](<C:/Users/GamerTech/Downloads/Double_Bounce_Universe (9).pdf>) | Section 7, “Quaternion Closure and the Snake,” pp. 39–43; start at p. 39 | Direct paper version of the three imaginary observers and real verifier. Section 23.3, p. 112, discusses changing real/imaginary roles under recursion. |
| [Shovelcat Theory 13 (2)](<C:/Users/GamerTech/Downloads/Shovelcat_Theory_13 (2).pdf>) | Section 3, “The Quaternion Processing Unit,” p. 8 | Defines i/j/k as what/where/when and w as the observer linking representation to evaluation. |
| [Vesica AI (1)](<C:/Users/GamerTech/Downloads/Vesica_AI (1).pdf>) | Section 7.2.2 and Figure 4, p. 10 | Explicit real observer orthogonal to three processing streams, with a diagram. |

These papers document the history of the model. Their additional physical and verification claims are not established by the quaternion identities. In particular, a unit norm is not evidence of semantic correctness, and the discussion treating 0.999… as less than 1 is not valid in the standard real numbers.

Other versions were found in Downloads, including Double_Bounce_Universe (2) through (6), (8), Shovelcat_Theory_13, Shovelcat_Theory_13 (1), Shovelcat_Theory_13B, and Vesica_AI. Desktop also contains Shovelcat_Theory_11_1 (1) (1).pdf, with quaternion material on p. 12. Prefer the specific passages above for this investigation; filenames alone do not establish which version is authoritative.

## Related code and notes

| Source | Relevant part |
|---|---|
| [Shovelcat Security README](<C:/Users/GamerTech/Desktop/Vesica AI/Shovelcat Security/README.md:5>) | The equation and framework overview. |
| [Earlier Euler–phi model](<C:/Users/GamerTech/Desktop/Vesica AI/Shovelcat Security/euler_phi_security.py:4>) | Predecessor equation without the hash fraction. |
| [Downloads security copy](<C:/Users/GamerTech/Downloads/crypto_euler_phi.py:6>) | Another copy of the SHA-based equation. |
| [Downloads security README](<C:/Users/GamerTech/Downloads/README (1).md:1>) | Expanded security project overview. |
| [Consciousness implementation](<C:/Users/GamerTech/Desktop/Vesica AI/Consciousness/quaternion_consciousness.py:563>) | Real observer plus what/where/when components; Hamilton product at lines 572–578 and integration at 602–628. |
| [Checker v3](<C:/Users/GamerTech/Desktop/Vesica AI/Shovelcat Security/ai_checker_v3.py:16>) | Symbolic/geometric/physical dimensions plus real context. |
| [Quaternion cylinder](<C:/Users/GamerTech/Downloads/quaternion_cylinder.py:58>) | Real observer axis and projections of imaginary rotations. |
| [Geometric media](<C:/Users/GamerTech/Downloads/geometric-media (1).ts:168>) | Maps SHA digest chunks to azimuth, polar angle, and magnitude. Computes the hash first. |
| [Colony security implementation](<D:/shovelcat-colony/app/src/core/crypto-euler-phi.ts:8>) | TypeScript version of the same SHA/Euler–phi equation. |
| [Colony quaternion chain](<D:/shovelcat-colony/app/src/core/quaternion-chain.ts:8>) | Real observer/output and three processing paths. |
| [Colony tensor axes](<D:/shovelcat-colony/app/src/core/tensor-axes.ts:13>) | Three conceptual streams plus scalar output. |
| [Strand derivation](<D:/shovelcat-colony/Shovelcat/strand-derivation-v0.2.md:30>) | Verifier coordinate w and the imaginary triad; explicitly identifies the real axis at line 78. |
| [Earlier colony paper](<D:/shovelcat-colony/companion/library/shovelcat_theory_v2_paper.md:12>) | Three domain series and an orthogonal observer. |

[encrypted_hamiltonian.py](<C:/Users/GamerTech/Desktop/Vesica AI/Shovelcat Security/encrypted_hamiltonian.py:232>) is related by theme, but its state operation is salted SHA-256 and HMAC. Here “Hamiltonian” refers to position/momentum dynamics, not Hamilton quaternions. The companion library also contains copies of the Desktop security sources.

## A precise extension of the confirmed equation

The following constructions are proposals developed during this retrieval, not equations claimed to have been found in the older files.

First split the original complex number:

\[
r=\varphi^{n+h},\qquad a=r\cos\theta,\qquad b=r\sin\theta,\qquad S=a+bi.
\]

### Independent imaginary channels and completed results

The minimal extension adds two real-valued coefficients c and d:

\[
Q=a+bi+cj+dk.
\]

Setting c=d=0 recovers S. To represent three complex slices sharing a real part, write

\[
S_i=a+bi,\quad S_j=a+cj,\quad S_k=a+dk,
\qquad Q=S_i+S_j+S_k-2a.
\]

The shared a is counted once. Simply summing the three slices would count it three times.

Completed scalar results can be accumulated explicitly:

\[
Q_t=(a+A_t)+b_ti+c_tj+d_tk,\qquad A_0=0,\qquad A_{t+1}=A_t+\delta_t.
\]

The next design decision is to define c, d, and each completed contribution δ_t. An accumulator preserves an aggregate; it does not retain every individual result unless a separate lossless encoding is specified. This construction imposes no unit-norm condition. If a fixed norm is desired, the components cannot all change independently.

### Different imaginary arrangements with exactly the same real component

Choose a unit imaginary direction

\[
u=u_1i+u_2j+u_3k,\qquad u_1^2+u_2^2+u_3^2=1.
\]

Then

\[
Q=\varphi^{n+h}e^{u\theta}
 =r\cos\theta+r\sin\theta\,(u_1i+u_2j+u_3k).
\]

For fixed r and θ, changing u changes the imaginary arrangement while preserving the real component r cos θ and magnitude r. At u=i this is exactly the original S. This is the most direct geometric interpretation of arranging different imaginary components around a common real value. The three imaginary coefficients are constrained, rather than independent storage slots. The quaternion exponential identity is documented in [Oregon State University's quaternion text, Section 2.2](https://books.physics.oregonstate.edu/GELG/qrot.html).

### What the algebra does not supply automatically

For real a, b and imaginary vectors v, w, Hamilton multiplication gives

\[
\operatorname{Re}((a+\mathbf v)(b+\mathbf w))=ab-\mathbf v\cdot\mathbf w.
\]

That is a specific combination, not an automatic rule that sends arbitrary completed computations to the real axis. Likewise, Q times its conjugate gives the real norm squared, but loses directional information. Shared real components must be defined or derived; the choice of labels alone does not establish a shared computation or a consensus test.

## Connection to the Lean SHA-256 challenge

The security code uses SHA-256 as an existing hash function and then gives the digest a geometric representation. This differs from reducing the work needed to compute SHA-256 itself.

The current [SHA submission](<C:/Users/GamerTech/Desktop/Vesica AI/lean-kernel-challenge/submissions_v4/sha256/Submission.lean:123>) already has a concrete shared contribution:

\[
a'=(T_1+\Sigma_0(a)+\operatorname{Maj}(a,b,c))\bmod2^{32},
\qquad e'=(T_1+d)\bmod2^{32}.
\]

This is a useful place to look for a shared real channel plus residual channels. In the source inspected on October 4, T1 is defined at line 124, NA/NE at 126–128, and t1 is already bound once per round at lines 146 and 159. The user is actively updating this file, so line locations may move.

A quaternion restatement of this sharing is not yet an optimization. The next useful experiment would establish an additional exact identity that removes work across multiple outputs, implement it with exact integer/word operations, prove it agrees with the reference, and measure kernel instruction counts. SHA-256's specified bitwise operations and addition modulo 2^32 must be preserved; see [NIST FIPS 180-4, Sections 4.1.2 and 6.2.2](https://nvlpubs.nist.gov/nistpubs/fips/nist.fips.180-4.pdf).

Keep the original digest H as bytes or an exact integer. The existing [normalize_hash](<C:/Users/GamerTech/Desktop/Vesica AI/Shovelcat Security/crypto_euler_phi.py:48>) converts it to a Python float, which loses digest information; that coordinate cannot stand in for the full hash. Retaining H/2^256 symbolically or as an exact rational avoids that particular loss. The existing verifier also compares full hash strings; the geometric coordinate is not its only check.

## Retrieval scope

This was a targeted search of relevant Desktop/Vesica AI, Downloads, Shovelcat Security, and colony sources, including text extraction from 58 distinct candidate PDFs. It is not a claim that every file on the computer has been indexed. No literal SHA-256 match was found in the extracted text of those PDFs; the strongest explicit SHA equation was in code and Markdown. Image-only text and differently worded discussions may need further inspection.

Original papers, security sources, and challenge submissions were not modified or executed during retrieval. This note is the new artifact.
