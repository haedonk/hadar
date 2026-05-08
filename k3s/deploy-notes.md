# Hadar Deploy Notes

## 2026-05-08 - Phase 3 Image Rebuilds

Git commit used for image tags:

```text
65708ed
```

Images built and pushed:

```text
haka9670/isolation-forest:65708ed
sha256:3d0076c07631651cb95aaf710a09199a1e29e6a8b4dbd17ad28bd50fadb23d39

haka9670/scoring-pipeline:65708ed
sha256:13d3525ead8052a37a7b0829f8d92f8b24840834fbfda143a2cb9f3872bfd076
```

Deployment manifests were updated to use the immutable `65708ed` tags instead
of `latest`. This pairs with `imagePullPolicy: IfNotPresent` so k3s does not
accidentally keep or reuse an ambiguous cached `latest` image.
