import unreal

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
select_actors = actor_subsystem.get_selected_level_actors() # type: ignore

print(select_actors[0].static_mesh_component.static_mesh.get_editor_property('static_materials'))