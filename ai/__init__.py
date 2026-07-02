"""FireRescue AI — Version 2 AI workspace.

Multi-model workspace: each AI capability (object detection, fire
detection, mapping, sensor fusion) is an independent module under this
package, with generic infrastructure in ai/shared/. Nothing here is
imported by the MVP backend; integration happens later through the
perception detector registry.
"""
